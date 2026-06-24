from workflow import app
from globals import (
    GraphStatus,
    create_initial_state,
    get_graph_status,
)
from langgraph.types import Command
import traceback

import json
from pprint import pprint


class WorkflowCLI:

    def __init__(self):
        self.thread_id = "first_thread"

    @property
    def config(self):
        return {
            "configurable": {
                "thread_id": self.thread_id
            }
        }

    def get_snapshot(self):
        return app.get_state(self.config)

    def show_status(self):
        snapshot = self.get_snapshot()

        status = get_graph_status(snapshot)

        print("\n====== 当前状态 ======")
        print(f"Thread: {self.thread_id}")
        print(f"Status: {status}")
        print(f"Next: {snapshot.next}")
        print("======================\n")

    def start_workflow(self):

        requirement = input("请输入需求:\n> ")

        state = create_initial_state(
            requirement=requirement
        )

        # 如果已经存在，就会fork 从根节点
        app.invoke(
            state,
            config=self.config
        )

        print("工作流已启动")

    def resume_workflow(self):

        app.invoke(
            None,
            config=self.config
        )

        print("继续执行完成")

    def human_interrupt(self):

        snapshot = self.get_snapshot()

        if not snapshot.tasks:
            print("没有中断节点")
            return

        task = snapshot.tasks[0]

        if not task.interrupts:
            print("没有中断节点")
            return

        interrupt_info = task.interrupts[0].value

        print("\n中断信息:")
        pprint(interrupt_info)

        feedback = input(
            "\n请输入人工反馈:\n> "
        )

        app.invoke(
            Command(
                resume=feedback
            ),
            config=self.config
        )

    def show_history(self):

        history = list(
            app.get_state_history(
                self.config
            )
        )

        print()

        for idx, state in enumerate(history):

            node = (
                state.next[0]
                if state.next
                else "END"
            )

            print(
                f"[{idx}] "
                f"{node}"
            )

        print()

    def inspect_checkpoint(self):

        history = list(
            app.get_state_history(
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

        print("\n====== STATE ======\n")

        pprint(state.values)

    def rollback(self):

        history = list(
            app.get_state_history(
                self.config
            )
        )

        self.show_history()

        idx = int(
            input(
                "\n回溯到哪个checkpoint?\n> "
            )
        )

        target = history[idx]

        fork_config = app.update_state(
            target.config,
            values=target.values,
        )

        app.invoke(
            None,
            fork_config
        )

        print("回溯执行完成")

    def switch_thread(self):

        thread_id = input(
            "\n输入Thread ID:\n> "
        )

        self.thread_id = thread_id

        print(
            f"切换到 {thread_id}"
        )

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

        print(
            f"\nToken: {token_size}"
        )

        print(
            f"Memory: {mem_size} bytes\n"
        )

    def menu(self):

        while True:

            print("""
========================
1. 查看状态
2. 启动工作流
3. 继续执行
4. 人工干预
5. 查看历史
6. 查看Checkpoint
7. 回溯Checkpoint
8. 查看State大小
9. 切换Thread
0. 退出
========================
""")

            choice = input("> ")

            try:

                if choice == "1":
                    self.show_status()

                elif choice == "2":
                    self.start_workflow()

                elif choice == "3":
                    self.resume_workflow()

                elif choice == "4":
                    self.human_interrupt()

                elif choice == "5":
                    self.show_history()

                elif choice == "6":
                    self.inspect_checkpoint()

                elif choice == "7":
                    self.rollback()

                elif choice == "8":
                    self.show_state_size()

                elif choice == "9":
                    self.switch_thread()

                elif choice == "0":
                    break

                else:
                    print("无效输入")

            except Exception:
                print("\n====== ERROR ======\n")

                traceback.print_exc()

                print("\n===================\n")


if __name__ == "__main__":

    WorkflowCLI().menu()