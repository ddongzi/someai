from globals.state import create_initial_state
import asyncio
from langgraph.types import Command
import traceback
from pprint import pformat

import json
from pprint import pprint
import logging
from workflow import MyWorkflow
from globals.logger import run_logger



class Thread:

    def __init__(self, workflow: MyWorkflow, thread_id: str = "first_thread"):
        self.thread_id = thread_id
        self.workflow = workflow

    @property
    def config(self):
        return {
            "configurable": {
                "thread_id": self.thread_id
            }
        }

    async def _do_event(self,state,config, event_queue: asyncio.Queue = None):
        stream = self.workflow.graph.astream_events(state, config, version="v2")    

        async for event in stream:
            if event_queue is not None:
                etype = event['event']
                data = event['data']
                # 统一放入队列
                await event_queue.put({"type": etype, "data": data})

        if event_queue is not None:
            await event_queue.put(None)

    async def start_workflow(self, event_queue: asyncio.Queue = None):
        state = create_initial_state()
        
        await self._do_event(state, self.config, event_queue)


    async def resume_workflow(self, checkpoint_id: str, interrupt_id: str, data: str, event_queue: asyncio.Queue = None):
   
        target = None
        async for state in self.workflow.graph.aget_state_history(self.config):
            if state.config.get("configurable", {}).get("checkpoint_id") == checkpoint_id:
                target = state
                break
        run_logger.info(f"正在从 Checkpoint ID: {target.config['configurable'].get('checkpoint_id')} resume...")

        resume_command = Command(resume={interrupt_id: data})
        if "approved" in data:

            await self._do_event(resume_command, target.config, event_queue)


    async def continue_workflow(self, event_queue: asyncio.Queue = None):
   
        await self._do_event(None, self.config, event_queue)
        
    async def get_history(self, limit: int = 20):
        
        result = []
        
        # 2. 使用 async for 循环遍历读取数据
        async for sp in self.workflow.graph.aget_state_history(self.config):
            result.append({
                'values': sp.values,
                'next': sp.next,
                'config': sp.config,
                'metadata': sp.metadata,
                'created_at': sp.created_at,
                'parent_config': sp.parent_config,
                'tasks': sp.tasks,
                'interrupts': sp.interrupts
            })      
            # 3. 达到限制的数量就停止获取
            if len(result) >= limit:
                break
                
        return result

  
    def inspect_checkpoint(self):
        history = list(
            self.workflow.graph.get_state_history(
                self.config
            )
        )

        self.show_history()

        idx = int(
            input(
                "\n查看哪个checkpoint?\n> "
            )
        )

        state = history[idx]

        run_logger.info("\n====== STATE ======\n")

        pprint(state.values)

    async def get_state(self):
        """ 获取当前的精简且完整的状态字典， 不能直接返回snapshot是复杂对象，不能直接json化 """
        snapshot = await self.workflow.graph.aget_state(self.config, subgraphs=True)
        
        # 如果当前线程没有任何状态（比如刚创建，还没运行过）
        if not snapshot or not snapshot.values:
            return {
                "connected": False,
                "values": {},
                "next": [],
                "checkpoint_id": None
            }
            
        return {
            "values": snapshot.values, 
            "next": list(snapshot.next), 
            "checkpoint_id": snapshot.config.get("configurable", {}).get("checkpoint_id"),
            "config": snapshot.config,
            "metadata": snapshot.metadata
        }


    async def replay(self, checkpoint_id: str,  event_queue: asyncio.Queue = None):
        target = None
        async for state in self.workflow.graph.aget_state_history(self.config):
            if state.config.get("configurable", {}).get("checkpoint_id") == checkpoint_id:
                target = state
                break
        run_logger.info(f"正在从 Checkpoint ID: {target.config['configurable'].get('checkpoint_id')} 重放执行...")

        await self._do_event(None,target.config, event_queue)  # 继续执行事件流
        run_logger.info("重放执行完成")



    def show_state_size(self):

        from utils import (
            calculate_total_tokens_for_pyobj,
            calculate_memory_size
        )

        snapshot = self.get_snapshot()

        token_size = (
            calculate_total_tokens_for_pyobj(
                snapshot.values
            )
        )

        mem_size = (
            calculate_memory_size(
                snapshot.values
            )
        )

        run_logger.info(
            f"\nToken: {token_size}"
        )

        run_logger.info(
            f"Memory: {mem_size} bytes\n"
        )
    async def clear_history(self):
        """
        显示当前 thread 的状态历史；若 clear=True，则物理删除 SQLite 中的相关历史。
        """
        # 1. 提取当前配置中的 thread_id
        thread_id = self.config.get("configurable", {}).get("thread_id")
        if not thread_id:
            run_logger.info("错误：配置中未检测到有效 thread_id！")
            return

        run_logger.info(f"正在尝试清空 Thread [{thread_id}] 的所有历史记录。（删除thread）...")
        
        try:
            await self.workflow.graph.checkpointer.adelete_thread(thread_id)
            run_logger.info(f"成功！已从 SQLite 数据库中彻底清除该 Thread 的所有快照。")
            
        except Exception as e:
            run_logger.info(f"清除失败，错误信息: {e}")

    async def fork(self, checkpoint_id: str, state: dict, event_queue: asyncio.Queue = None):
        target = None
        async for sp in self.workflow.graph.aget_state_history(self.config):
            if sp.config.get("configurable", {}).get("checkpoint_id") == checkpoint_id:
                target = sp
                break
                
        if not target:
            raise ValueError(f"未找到指定的 Checkpoint ID: {checkpoint_id}")

        run_logger.info(f"从 Checkpoint ID: {checkpoint_id} 开始分叉并更新状态...")

        # 1. 使用 update_state 将用户传入的 state 写入到该 checkpoint 上
        # 这会在底层自动生成一个处于新分叉分支的 fork_config,  这是一个新的checkpoint。复制而来类似
        fork_config = await self.workflow.graph.aupdate_state(
            target.config, 
            state, 
        )

        # 2. 使用带有新状态的分叉配置 fork_config 去继续执行事件流
        # 此时无需单独传旧的 state，因为新状态已经持久化在 fork_config 对应的 Checkpoint 中了
        await self._do_event(None, fork_config, event_queue)  
