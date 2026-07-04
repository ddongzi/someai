import React, { useState } from 'react';

function ForkStatePanel({ initialState, onSubmit, onCancel }) {
  // 将初始状态转化为漂亮的 JSON 字符串
  const [stateStr, setStateStr] = useState(JSON.stringify(initialState, null, 2));

  const handleSubmit = () => {
    try {
      const parsed = JSON.parse(stateStr);
      onSubmit(parsed);
    } catch (e) {
      alert("JSON 格式错误，请检查括号与逗号是否正确。");
    }
  };

  return (
    <div className="flex flex-col h-full space-y-3">
      {/* 头部标题与操作 */}
      <div className="flex justify-between items-center">
        <h4 className="text-sm font-semibold text-slate-700">🛠️ 修改 State 并分叉执行</h4>
        <div className="space-x-2">
          <button 
            onClick={onCancel} 
            className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1"
          >
            取消
          </button>
          <button 
            onClick={handleSubmit} 
            className="text-xs bg-amber-500 text-white px-3 py-1 rounded hover:bg-amber-600 transition-colors"
          >
            确认 Fork
          </button>
        </div>
      </div>

      {/* JSON 编辑文本框 */}
      <textarea
        className="w-full flex-1 p-2 font-mono text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-amber-500 bg-slate-50"
        value={stateStr}
        onChange={(e) => setStateStr(e.target.value)}
        rows={8}
        placeholder="{}"
      />
    </div>
  );
}

export default ForkStatePanel;
