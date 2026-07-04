export default function TopBar({ 
  sseConnected, 
  onStart, 
  onContinue, 
  onClear,
  onReplay, // 🎯 新增：重放回调
  onFork    // 🎯 新增：分叉回调
}) {
  return (
    <div className="w-full h-14 bg-white px-4 flex items-center justify-between text-xs border-b border-slate-200 shrink-0 shadow-sm">
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2">
          <span className={`h-2.5 w-2.5 rounded-full ${sseConnected ? 'bg-emerald-500 shadow-[0_0_6px_#10b981]' : 'bg-rose-500'}`}></span>
          <span className="font-bold text-slate-700">SSE: {sseConnected ? 'CONNECTED' : 'DISCONNECTED'}</span>
        </div>
        <div className="bg-blue-50 border border-blue-200 px-3 py-1 rounded">
          <span className="text-blue-600/70 font-bold">Thread:</span>{' '}
          <span className="text-blue-700 font-bold">first_thread</span>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        {/* 全局主核心操作 */}
        <button onClick={onStart} className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-3 py-1.5 rounded shadow-xs transition cursor-pointer">
          🚀 启动工作流
        </button>
        <button onClick={onContinue} className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-3 py-1.5 rounded shadow-xs transition cursor-pointer">
          ⚡ 继续执行
        </button>

        {/* 🎯 新增：时间旅行控制（Replay & Fork） */}
        <button onClick={onReplay} className="bg-amber-500 hover:bg-amber-600 text-white font-bold px-3 py-1.5 rounded shadow-xs transition cursor-pointer">
          ↩️ 从此处重放
        </button>
        <button onClick={onFork} className="bg-purple-600 hover:bg-purple-700 text-white font-bold px-3 py-1.5 rounded shadow-xs transition cursor-pointer">
          🌿 创建分叉分支
        </button>

        {/* 毁坏性危险操作隔离放置 */}
        <button onClick={onClear} className="bg-white hover:bg-slate-50 text-slate-600 font-bold px-3 py-1.5 rounded border border-slate-300 shadow-xs transition cursor-pointer">
          🗑️ 清空重置
        </button>
      </div>
    </div>
  );
}
