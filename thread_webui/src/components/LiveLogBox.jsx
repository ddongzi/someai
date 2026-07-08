import React, { useEffect, useRef } from 'react';

export default function LiveLogBox({ logs, onClear }) {
  const containerRef = useRef(null);

  // 💡 体验优化：当有新日志进来时，内容区自动滚动到最底部
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  // 💡 核心优化：亮色主题下，采用低饱和度、高对比度的莫兰迪色系进行事件分类
  const getLogTypeStyles = (type) => {
    const lowerType = type.toLowerCase();
    
    // 大模型流式输出 (打字机)
    if (lowerType.includes('chat_model_stream')) {
      return { label: 'bg-emerald-50 text-emerald-700 border border-emerald-200', msg: 'text-emerald-900 font-medium' };
    }
    // 工具开始执行
    if (lowerType.includes('tool_start')) {
      return { label: 'bg-sky-50 text-sky-700 border border-sky-200', msg: 'text-sky-900 font-semibold italic' };
    }
    // 工具执行完毕
    if (lowerType.includes('tool_end')) {
      return { label: 'bg-indigo-50 text-indigo-700 border border-indigo-200', msg: 'text-slate-600' };
    }
    // 工作流节点生命周期
    if (lowerType.includes('chain_start') || lowerType.includes('chain_end')) {
      return { label: 'bg-amber-50 text-amber-700 border border-amber-200', msg: 'text-amber-900' };
    }
    // 默认兜底日志样式
    return { label: 'bg-slate-100 text-slate-600 border border-slate-200', msg: 'text-slate-800' };
  };

  return (
    <div className="w-full h-full flex flex-col font-mono text-xs select-none bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
      {/* 头部控制栏：干净的亮白分界 */}
      <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-2">
          {/* 亮色系专用的淡绿色动态呼吸灯 */}
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="font-bold text-slate-700 tracking-wide">📡 SSE 实时流日志监控</span>
          <span className="text-slate-500 px-1.5 py-0.5 rounded bg-slate-200/60 text-[10px] scale-90 origin-left font-semibold">
            {logs.length} 条记录
          </span>
        </div>
        <button 
          onClick={onClear} 
          className="text-slate-400 hover:text-rose-600 hover:bg-rose-50 px-2 py-0.5 border border-transparent hover:border-rose-200 rounded-md transition-all font-medium text-[11px]"
        >
          [清屏]
        </button>
      </div>

      {/* 内容展示区：护眼浅灰乳白底色 */}
      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 space-y-2 bg-slate-50/50 text-slate-800 selection:bg-indigo-100 scrollbar-thin scrollbar-thumb-slate-200"
      >
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 italic space-y-1">
            <span className="text-sm">等候后台数据传输...</span>
            <span className="text-[10px] text-slate-300 not-italic uppercase tracking-wider">Codeteam Agent Offline</span>
          </div>
        ) : (
          logs.map((log) => {
            const styles = getLogTypeStyles(log.type);
            return (
              <div key={log.id} className="leading-6 whitespace-pre-wrap flex items-start space-x-2 hover:bg-slate-200/30 px-2 py-1 rounded-md group transition-all border border-transparent hover:border-slate-100">
                {/* 时间戳：优雅淡灰色 */}
                <span className="text-slate-400 font-normal shrink-0 tracking-tight select-none">
                  [{log.timestamp}]
                </span>
                
                {/* 格式化标签：低饱和度莫兰迪块
                <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider shrink-0 scale-95 origin-top select-none ${styles.label}`}>
                  {log.type.replace('on_', '').toUpperCase()}
                </span> */}
                
                {/* 真实消息体：清晰直观、高对比度 */}
                <span className={`flex-1 break-all ${styles.msg}`}>
                  {log.message}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
