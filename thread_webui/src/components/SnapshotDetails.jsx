export default function SnapshotDetails({ checkpoint }) {
  // 🎯 动态提取中断数据（兼容 LangGraph 各种主流的数据解构格式）
  const getInterrupts = () => {
    if (!checkpoint) return [];
    
    // 路径 A：标准 LangGraph 的 tasks 节点内
    if (Array.isArray(checkpoint.tasks)) {
      const taskWithInterrupt = checkpoint.tasks.find(t => t.interrupts && t.interrupts.length > 0);
      if (taskWithInterrupt) return taskWithInterrupt.interrupts;
    }
    
    // 路径 B：部分后端直接把中断拍平到了最外层或者 metadata 里
    if (Array.isArray(checkpoint.interrupts)) return checkpoint.interrupts;
    if (Array.isArray(checkpoint.metadata?.interrupts)) return checkpoint.metadata.interrupts;
    
    return [];
  };

  const interrupts = getInterrupts();

  return (
    <div className="w-full h-full flex flex-col text-xs">
      <div className="p-3 border-b border-slate-200 bg-slate-50 font-bold text-slate-600">
        🔍 选中快照详情 (Snapshot)
      </div>
      <div className="flex-1 overflow-y-auto p-3 bg-white">
        {!checkpoint ? (
          <div className="text-slate-400 italic text-center p-4">请在左侧时间线选择任意节点查看状态快照</div>
        ) : (
          <div className="space-y-4">
            {/* 1. 元数据配置 */}
            <div>
              <div className="text-slate-400 font-bold uppercase mb-1 text-[10px]">元数据配置:</div>
              <div className="bg-slate-50 p-2 border border-slate-200 rounded space-y-1 text-slate-600">
                <div><span className="text-slate-400 font-normal">Node:</span> {Array.isArray(checkpoint.next) ? checkpoint.next.join(', ') : (checkpoint.next || 'End')}</div>
                <div className="truncate"><span className="text-slate-400 font-normal">ID:</span> {checkpoint?.config?.configurable?.checkpoint_id}</div>
                <div className="truncate"><span className="text-slate-400 font-normal">PID:</span> {checkpoint?.parent_config?.configurable?.checkpoint_id}</div>
                <div><span className="text-slate-400 font-normal">Time:</span> {checkpoint.created_at || 'Unknown'}</div>
              </div>
            </div>

            {/* 🎯 2. 新增：高亮挂起中断信号模块 (仅在有中断数据时渲染) */}
            {interrupts.length > 0 && (
              <div className="animate-fade-in">
                <div className="text-amber-600 font-bold uppercase mb-1 text-[10px] flex items-center space-x-1">
                  <span>⚠️ 挂起中断信号 (Interrupts):</span>
                </div>
                <div className="bg-amber-50 border border-amber-200 rounded p-3 text-amber-900 space-y-2 shadow-xs">
                  {interrupts.map((item, index) => (
                    <div key={index} className="space-y-1">
                      <div className="font-bold flex items-center text-amber-800">
                        📌 中断事件 #{index + 1}
                      </div>
                      <pre className="w-full p-2 bg-white/80 border border-amber-200/60 rounded text-[10px] text-amber-950 overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
                        {typeof item === 'object' ? JSON.stringify(item, null, 2) : String(item)}
                      </pre>
                    </div>
                  ))}
           
                </div>
              </div>
            )}

            {/* 3. State 内存树状只读区 */}
            <div className="flex flex-col min-h-0">
              <div className="text-slate-400 font-bold uppercase mb-1 text-[10px]">State Values (树状只读):</div>
              <pre className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded text-[11px] text-indigo-900 overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed max-h-96">
                {JSON.stringify(checkpoint.values, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
