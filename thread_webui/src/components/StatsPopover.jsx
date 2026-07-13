import { useState, useEffect } from 'react';
import { getLLMStat } from '../api';

export default function StatsPopover({ onClose }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  
  // 核心统计状态
  const [summary, setSummary] = useState({
    today: { input: 0, output: 0, total: 0, cache: 0, count: 0 },
    allTime: { input: 0, output: 0, total: 0, cache: 0, count: 0 }
  });
  const [recentLogs, setRecentLogs] = useState([]);

  useEffect(() => {
    async function loadStats() {
      setLoading(true);
      setError(false);
      try {
        const data = await getLLMStat();
        const list = Array.isArray(data) ? data : [data];

        // 基础统计结构
        const today = { input: 0, output: 0, total: 0, cache: 0, count: 0 };
        const allTime = { input: 0, output: 0, total: 0, cache: 0, count: 0 };
        
        const now = new Date();
        const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();

        list.forEach(item => {
          const itemTime = new Date(item.timestamp).getTime();
          const isToday = itemTime >= startOfToday;

          const input = item.usage?.input_tokens ?? 0;
          const output = item.usage?.output_tokens ?? 0;
          const total = item.usage?.total_tokens ?? 0;
          const cache = item.usage?.input_token_details?.cache_read ?? 0;

          // 累加历史总计
          allTime.input += input;
          allTime.output += output;
          allTime.total += total;
          allTime.cache += cache;
          allTime.count += 1;

          // 累加今日统计
          if (isToday) {
            today.input += input;
            today.output += output;
            today.total += total;
            today.cache += cache;
            today.count += 1;
          }
        });

        setSummary({ today, allTime });
        // 仅保留最近 3 次的明细，避免拉得太长
        setRecentLogs(list.slice(0, 10));

      } catch (err) {
        console.error('Fetch stats error:', err);
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  return (
    <div className="absolute left-0 mt-2 w-80 bg-white border border-slate-200 rounded-lg shadow-xl p-4 z-50 text-slate-600 animate-in fade-in slide-in-from-top-1 duration-200">
      {/* 头部固定 */}
      <div className="flex justify-between items-center border-b border-slate-100 pb-2 mb-3">
        <span className="font-bold text-slate-800 text-sm flex items-center space-x-1">
          <span>📊</span> <span>Token 用量看板</span>
        </span>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xs cursor-pointer">✕</button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8 text-slate-400 text-xs">
          <span className="animate-spin mr-2">⏳</span> 正在统计中...
        </div>
      ) : error ? (
        <div className="text-rose-500 py-6 text-center text-xs font-medium">❌ 获取统计失败</div>
      ) : (
        <div className="space-y-4">
          
          {/* 维度 1：今日用量卡片 */}
          <div className="bg-emerald-50/60 border border-emerald-100 rounded-lg p-2.5">
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-emerald-800 font-bold text-[11px] bg-emerald-100 px-1.5 py-0.5 rounded">📅 今日内 (24h)</span>
              <span className="text-[10px] text-emerald-600/80 font-medium">共请求 {summary.today.count} 次</span>
            </div>
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs text-slate-600 font-mono">
              <div className="flex justify-between">
                <span className="text-slate-400">输入:</span>
                <span>{summary.today.input}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">输出:</span>
                <span>{summary.today.output}</span>
              </div>
              <div className="col-span-2 flex justify-between border-t border-emerald-200/50 pt-1 mt-0.5 font-bold text-emerald-700">
                <span>总用量 (Total):</span>
                <span>{summary.today.total}</span>
              </div>
              {summary.today.cache > 0 && (
                <div className="col-span-2 flex justify-between text-[10px] text-emerald-600 italic">
                  <span>└ 节省命中 (Cache):</span>
                  <span>{summary.today.cache}</span>
                </div>
              )}
            </div>
          </div>

          {/* 维度 2：全部时间卡片 */}
          <div className="bg-indigo-50/60 border border-indigo-100 rounded-lg p-2.5">
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-indigo-800 font-bold text-[11px] bg-indigo-100 px-1.5 py-0.5 rounded">🌍 全部时间</span>
              <span className="text-[10px] text-indigo-600/80 font-medium">共请求 {summary.allTime.count} 次</span>
            </div>
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs text-slate-600 font-mono">
              <div className="flex justify-between">
                <span className="text-slate-400">总输入:</span>
                <span>{summary.allTime.input}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">总输出:</span>
                <span>{summary.allTime.output}</span>
              </div>
              <div className="col-span-2 flex justify-between border-t border-indigo-200/50 pt-1 mt-0.5 font-bold text-indigo-700">
                <span>累计总量:</span>
                <span>{summary.allTime.total}</span>
              </div>
            </div>
          </div>

          {/* 底部最近微小明细（可选展示，最多3条） */}
          {recentLogs.length > 0 && (
            <div className="border-t border-slate-100 pt-2">
              <div className="text-[10px] text-slate-400 font-bold mb-1">⚡ 最近请求明细</div>
              <div className="space-y-1 max-h-24 overflow-y-auto pr-1">
                {recentLogs.map((item, idx) => (
                  <div key={idx} className="flex justify-between text-[10px] font-mono text-slate-500 bg-slate-50 px-1.5 py-0.5 rounded">
                    <span className="truncate max-w-[120px]">{item.model_name}</span>
                    <span>Total: <strong className="text-slate-700">{item.usage?.total_tokens}</strong></span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
        </div>
      )}
    </div>
  );
}