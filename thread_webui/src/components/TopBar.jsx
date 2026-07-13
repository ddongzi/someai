import { useState } from 'react';
import { getLLMStat } from '../api';
import StatsPopover from './StatsPopover';

export default function TopBar({
  sseConnected,
  onStart,
  onContinue,
  onClear,
  onReplay,
  onFork
}) {
  const [showStats, setShowStats] = useState(false);

  return (
    <div className="w-full h-14 bg-white px-4 flex items-center justify-between text-xs border-b border-slate-200 shrink-0 shadow-sm relative">
      <div className="flex items-center space-x-6">
        {/* SSE 状态 */}
        <div className="flex items-center space-x-2">
          <span className={`h-2.5 w-2.5 rounded-full ${sseConnected ? 'bg-emerald-500 shadow-[0_0_6px_#10b981]' : 'bg-rose-500'}`}></span>
          <span className="font-bold text-slate-700">SSE: {sseConnected ? 'CONNECTED' : 'DISCONNECTED'}</span>
        </div>

        {/* Thread 信息 */}
        <div className="bg-blue-50 border border-blue-200 px-3 py-1 rounded">
          <span className="text-blue-600/70 font-bold">Thread:</span>{' '}
          <span className="text-blue-700 font-bold">first_thread</span>
        </div>
        {/* 📊 Token 统计入口 */}
        <div className="relative">
          <button
            onClick={() => setShowStats(!showStats)}
            className="flex items-center space-x-1 text-slate-500 hover:text-indigo-600 font-medium transition cursor-pointer bg-slate-50 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 px-2.5 py-1 rounded"
          >
            <span>📊</span>
            <span className="underline decoration-dotted">LLM 用量历史</span>
          </button>

          {/* 🎯 挂载新组件 */}
          {showStats && <StatsPopover onClose={() => setShowStats(false)} />}
        </div>
      </div>

      {/* 右侧操作按钮保持不变 */}
      <div className="flex items-center space-x-2">
        <button onClick={onStart} className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-3 py-1.5 rounded shadow-xs transition cursor-pointer">
          🚀 启动工作流
        </button>
        <button onClick={onContinue} className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-3 py-1.5 rounded shadow-xs transition cursor-pointer">
          ⚡ 继续执行
        </button>

        <button onClick={onReplay} className="bg-amber-500 hover:bg-amber-600 text-white font-bold px-3 py-1.5 rounded shadow-xs transition cursor-pointer">
          ↩️ 从此处重放
        </button>
        <button onClick={onFork} className="bg-purple-600 hover:bg-purple-700 text-white font-bold px-3 py-1.5 rounded shadow-xs transition cursor-pointer">
          🌿 创建分叉分支
        </button>

        <button onClick={onClear} className="bg-white hover:bg-slate-50 text-slate-600 font-bold px-3 py-1.5 rounded border border-slate-300 shadow-xs transition cursor-pointer">
          🗑️ 清空重置
        </button>
      </div>
    </div>
  );
}