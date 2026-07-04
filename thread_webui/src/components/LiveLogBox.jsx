export default function LiveLogBox({ logs, onClear }) {
  return (
    <div className="w-full h-full flex flex-col text-xs">
      <div className="px-4 py-2 border-b border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
        <span className="font-bold text-slate-600">📡 SSE 实时流日志监控</span>
        <button onClick={onClear} className="text-slate-400 hover:text-slate-600 underline font-bold">
          [清屏]
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-1.5 font-mono bg-slate-200 text-slate-100 selection:bg-slate-700">
        {logs.length === 0 ? (
          <div className="text-slate-500 italic">等待后台事件流触发输入...</div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="leading-5 whitespace-pre-wrap">
              <span className="text-slate-500">[{log.timestamp}]</span>{' '}
              <span className="text-slate-400 font-bold">[{log.type.toUpperCase()}]</span>{' '}
              <span className="text-slate-400" >{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
