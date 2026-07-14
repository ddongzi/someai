import { useState, useEffect } from 'react';

export default function InterruptPanel({ interrupts = [], onSubmit }) {
  // 1. 核心状态：当前正在查看并操作哪一个中断
  const [activeIntIdx, setActiveIntIdx] = useState(0);

  // 2. 状态隔离矩阵：使用 `[字段_索引]` 的结构完美保存用户在不同 Tab 切换时的所有输入
  const [inputStates, setInputStates] = useState({});

  // 当传入的新快照或中断列表变化时，自动初始化各节点状态
  useEffect(() => {
    setActiveIntIdx(0);
    const initialStates = {};
    interrupts.forEach((_, idx) => {
      initialStates[`mode_${idx}`] = 'json';
      initialStates[`json_${idx}`] = '{\n  "approved": true\n}';
      initialStates[`text_${idx}`] = '';
      initialStates[`checks_${idx}`] = { verify_data: true, bypass_security: false };
    });
    setInputStates(initialStates);
  }, [interrupts]);

  if (!interrupts || interrupts.length === 0) return null;

  // 快捷提取当前高亮 Tab 专属的动态变量
  const currentMode = inputStates[`mode_${activeIntIdx}`] || 'json';
  const currentJson = inputStates[`json_${activeIntIdx}`] || '';
  const currentText = inputStates[`text_${activeIntIdx}`] || '';
  const currentChecks = inputStates[`checks_${activeIntIdx}`] || { verify_data: true, bypass_security: false };

  // 通用状态修改器
  const updateState = (keySuffix, value) => {
    setInputStates(prev => ({
      ...prev,
      [`${keySuffix}_${activeIntIdx}`]: value
    }));
  };

  // 🎯 原子提交：只打包、处理、发送当前被激活的那“唯一一个”中断
  const handleSingleSubmit = (e) => {
    e.preventDefault();
    let payload = {};

    if (currentMode === 'json') {
      try {
        payload = JSON.parse(currentJson);
      } catch {
        alert('💥 JSON 语法错误，请检查输入格式后再进行单项解锁');
        return;
      }
    } else if (currentMode === 'checkbox') {
      payload = { flags: currentChecks };
    } else {
      payload = { text: currentText };
    }

    // 🚀 精准针对性发射：只带上当前这一个中断的原始标记、以及用户针对它的输入
    onSubmit({
      target_index: activeIntIdx,
      raw_interrupt: interrupts[activeIntIdx],
      response_data: payload
    });
  };

  return (
    <div className="w-full h-full flex flex-col text-xs text-left">
      {/* 顶部指示栏 */}
      <div className="font-bold text-amber-600 mb-3 flex items-center space-x-2 shrink-0 border-b border-amber-100 pb-2">
        <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse"></span>
        <span>⚡ 中断 共{interrupts.length}个</span>
      </div>

      {/* 选项卡：在并行的多个中断之间顺畅切流 */}
      <div className="flex space-x-1 overflow-x-auto border-b border-slate-200 pb-2 mb-3 shrink-0 scrollbar-none">
        {interrupts.map((inter, idx) => {
          const isActive = activeIntIdx === idx;
          const title = typeof inter === 'object' 
            ? inter.action || inter.reason || `中断 #${idx + 1}` 
            : String(inter).substring(0, 12);

          return (
            <button
              key={idx} type="button" onClick={() => setActiveIntIdx(idx)}
              className={`px-3 py-1.5 rounded-t font-bold transition whitespace-nowrap cursor-pointer border ${
                isActive 
                  ? 'bg-amber-500 text-white border-amber-500 shadow-xs' 
                  : 'bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100'
              }`}
            >
              ⚠️ #{idx + 1} {title}
            </button>
          );
        })}
      </div>

      {/* 动态同步的拦截原因预览框 */}
      <div className="mb-3 p-2 bg-slate-50 border border-slate-200 rounded shrink-0">
        <div className="text-[10px] text-slate-400 font-bold mb-1 uppercase">当前选中中断的上下文:</div>
        <pre className="text-[10px] text-slate-700 font-mono overflow-x-auto whitespace-pre-wrap max-h-16">
          {typeof interrupts[activeIntIdx] === 'object' 
            ? JSON.stringify(interrupts[activeIntIdx], null, 2) 
            : String(interrupts[activeIntIdx])}
        </pre>
      </div>

      {/* 表单核心区：onSubmit 变为处理单点发射 */}
      <form onSubmit={handleSingleSubmit} className="flex-1 flex flex-col justify-between min-h-0">
        {/* 输入模式子标签 */}
        <div className="flex space-x-1 p-0.5 bg-slate-100 rounded w-max border border-slate-200 shrink-0">
          {['json', 'checkbox', 'text'].map((t) => (
            <button
              key={t} type="button" onClick={() => updateState('mode', t)}
              className={`px-2.5 py-1 rounded font-bold uppercase text-[10px] transition cursor-pointer ${
                currentMode === t 
                  ? 'bg-white text-slate-800 border border-slate-200 shadow-xs' 
                  : 'text-slate-400 hover:text-slate-600'
              }`}
            >
              {t === 'json' ? '⚙️ JSON' : t === 'checkbox' ? '☑️ Checkbox' : '📝 Text'}
            </button>
          ))}
        </div>

        {/* 输入编辑区：内容随 activeIntIdx 的变化在内存中隔离保存和展现 */}
        <div className="flex-1 my-3 min-h-0">
          {currentMode === 'json' && (
            <textarea 
              value={currentJson} 
              onChange={(e) => updateState('json', e.target.value)} 
              className="w-full h-full p-2 bg-slate-50 border border-slate-200 rounded font-mono text-[11px] text-slate-700 focus:outline-none focus:border-indigo-400 focus:bg-white resize-none" 
            />
          )}
          {currentMode === 'checkbox' && (
            <div className="p-3 bg-slate-50 border border-slate-200 rounded grid grid-cols-2 gap-2 h-full overflow-y-auto">
              {Object.keys(currentChecks).map((k) => (
                <label key={k} className="flex items-center space-x-2 bg-white p-2 border border-slate-200 rounded cursor-pointer hover:bg-slate-50/50">
                  <input 
                    type="checkbox" 
                    checked={currentChecks[k]} 
                    onChange={(e) => updateState('checks', { ...currentChecks, [k]: e.target.checked })} 
                    className="accent-indigo-600 rounded" 
                  />
                  <span className="text-slate-600 font-bold">{k}</span>
                </label>
              ))}
            </div>
          )}
          {currentMode === 'text' && (
            <textarea 
              value={currentText} 
              onChange={(e) => updateState('text', e.target.value)} 
              placeholder="输入当前中断的专项处理指令..." 
              className="w-full h-full p-2 bg-slate-50 border border-slate-200 rounded font-mono text-[11px] text-slate-700 focus:outline-none focus:border-indigo-400 focus:bg-white resize-none" 
            />
          )}
        </div>

        {/* 底部按钮：就近对当页做出明确发射动作 */}
        <div className="flex items-center justify-end pt-2 border-t border-slate-100 shrink-0">
          <button 
            type="submit" 
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-4 py-2 rounded transition shadow-xs cursor-pointer w-full text-center"
          >
            ⚡ 提交中断 #{activeIntIdx + 1} 响应
          </button>
        </div>
      </form>
    </div>
  );
}
