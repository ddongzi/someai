import { useState, useEffect, useCallback } from 'react';
import TopBar from './components/TopBar';
import CheckpointList from './components/CheckpointList';
import LiveLogBox from './components/LiveLogBox';
import InterruptPanel from './components/InterruptPanel';
import SnapshotDetails from './components/SnapshotDetails';
import { getState, startWorkflow, getHistory, replay, fork, API_BASE_URL, clear, interruptSubmit, continueWL } from './api';
import { useSSE } from './hooks/useSSE';
import ForkStatePanel from './components/ForkStatePanel';


export default function App() {
  const [sseConnected] = useState(true);
  const [checkpoints, setCheckpoints] = useState([]);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sseEnabled, setSseEnabled] = useState(false); // 核心：流的总控开关
  // 1. 声明视图模式状态: 'interrupt' | 'fork' | 'none'
  const [editMode, setEditMode] = useState('none');
  const [forkData, setForkData] = useState(null);

  useEffect(() => {
    if (selectedCheckpoint?.interrupts?.length > 0) {
      setEditMode('interrupt');
    } else {
      setEditMode('none');
    }
  }, [selectedCheckpoint]);

  // 3. 点击 Fork 按钮，切换到分叉编辑模式
  const handleForkClick = () => {
    setEditMode('fork');
    // 浅拷贝当前的 state 作为编辑的初始数据
    setForkData(selectedCheckpoint?.values || {});
  };

  // 🎯 高内聚的日志追加函数：默认类型为 'info'
  const addLog = useCallback((message, type = 'info') => {
    setLogs((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`, // 生成绝对唯一的ID（时间戳+随机数）
        timestamp: new Date().toLocaleTimeString(), // 自动抓取当前本地时间
        type, // 'info' | 'agent' | 'error' | 'success'
        message,
      },
    ]);
  }, []);

  const { isConnected, disconnect } = useSSE({
    enabled: sseEnabled,
    onMessage: (data) => {
      console.log('SSE Message:', data);
      addLog(`SSE: ${JSON.stringify(data)}`, 'info');
    },
    onError: (e) => {
      setSseEnabled(false); // 流挂了，自动关闭前端开关状态
    }
  });

  // 🔄 历史快照自动刷新：只要 SSE 在传输，就每 10 秒拉取一次最新历史
  const refreshHistory = useCallback(async () => {
    try {
      const historyList = await getHistory();
      setCheckpoints(historyList);
    } catch (err) {
      console.error('刷新历史快照失败:', err);
    }
  }, []);

  useEffect(() => {
    if (!isConnected) return undefined;
    // 立即拉一次，再启动 10 秒轮询
    refreshHistory();
    const timer = setInterval(refreshHistory, 10000);
    return () => clearInterval(timer);
  }, [isConnected, refreshHistory]);
  const handleStart = async () => {
    addLog('🚀 手动初始化 LangGraph 工作流...', 'info');

    await startWorkflow();
    setSseEnabled(true);

  };
  const handleReplay = async () => {
    addLog('🔄 重放指定 Checkpoint...', 'info');
    var checkpoint_id = selectedCheckpoint['config']['configurable']['checkpoint_id'];
    await replay(checkpoint_id);
    setSseEnabled(true);
  };
  const handleContinue = async () => {
    addLog('⚡ 继续执行工作流...', 'info');
    await continueWL();
    setSseEnabled(true);
  }
  const handleClear = async () => {
    addLog('🧹 清理所有历史记录...', 'info');
    await clear();
    setSseEnabled(true);
  };
  const handleInterruptSubmit = async (payload) => {
    addLog('🚀 提交人工干预数据...', 'info');
    const interrupt = payload['raw_interrupt'];
    const checkpoint_id = selectedCheckpoint['config']['configurable']['checkpoint_id'];
    const interrupt_id = interrupt['id'];
    const data = payload['response_data'];
    await interruptSubmit(checkpoint_id, interrupt_id, data);
    setSseEnabled(true);
  };
  // 4. 提交 Fork 修改
  const handleForkSubmit = async (updatedState) => {
    // 这里调用您的 LangGraph 后端 fork 接口
    // await api.forkWorkflow(selectedCheckpoint.id, updatedState);
    var checkpoint_id = selectedCheckpoint['config']['configurable']['checkpoint_id'];

    await fork(checkpoint_id, updatedState);
    // 提交成功后，重置视图
    setEditMode('none');
    setSseEnabled(true);

  };
  useEffect(() => {
    const initData = async () => {
      try {
        const historyList = await getHistory();
        setCheckpoints(historyList);
      } catch (err) {
        console.error(err);
      }
    };
    initData();
  }, []);
  return (
    <div className="w-full h-screen flex flex-col bg-slate-50 text-slate-800 font-mono antialiased overflow-hidden select-none">
      <TopBar
        sseConnected={sseConnected}
        onStart={handleStart}
        onContinue={handleContinue}
        onClear={handleClear}
        onReplay={handleReplay}
        onFork={handleForkClick}

      />

      <div className="flex-1 w-full flex overflow-hidden border-t border-slate-200">

        <div className="w-80 h-full bg-white border-r border-slate-200 flex flex-col shrink-0">
          <CheckpointList
            checkpoints={checkpoints}
            selectedId={selectedCheckpoint?.config?.configurable?.checkpoint_id || null}
            onSelect={setSelectedCheckpoint}
          />
        </div>

        <div className="flex-1 h-full flex flex-col min-w-0 bg-slate-50">
          <div className="flex-1 border-b border-slate-200 overflow-hidden">
            <LiveLogBox logs={logs} onClear={() => setLogs([])} />
          </div>

          <div className="h-100 bg-white p-4 overflow-y-auto border-t border-slate-200">
            {/* 模式 1：显示中断输入 */}
            {editMode === 'interrupt' && (
              <InterruptPanel
                interrupts={selectedCheckpoint?.interrupts || []}
                onSubmit={handleInterruptSubmit}
              />
            )}

            {/* 模式 2：显示 Fork 状态修改 */}
            {editMode === 'fork' && (
              <ForkStatePanel
                initialState={forkData}
                onSubmit={handleForkSubmit}
                onCancel={() => setEditMode(selectedCheckpoint?.interrupts?.length > 0 ? 'interrupt' : 'none')}
              />
            )}

            {/* 模式 3：无中断也未点击 Fork */}
            {editMode === 'none' && (
              <div className="text-slate-400 text-center py-8 text-sm">
                没有什么可编辑的。
              </div>
            )}
          </div>
        </div>

        <div className="w-96 h-full bg-white border-l border-slate-200 flex flex-col shrink-0">
          <SnapshotDetails checkpoint={selectedCheckpoint} />
        </div>

      </div>
    </div>
  );
}
