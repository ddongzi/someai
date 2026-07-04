export default function CheckpointList({ checkpoints, selectedId, onSelect }) {
  return (
    <div className="w-full h-full flex flex-col text-xs">
      <div className="p-3 border-b border-slate-200 bg-slate-50 font-bold text-slate-600">
        🕒 CHECKPOINT 历史快照
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1 bg-white">
        {checkpoints.length === 0 ? (
          <div className="text-center text-slate-400 p-4 italic">暂无快照数据</div>
        ) : (
          checkpoints.map((cp,i) => (
            <div
              key={cp['config']['configurable']['checkpoint_id']}
              onClick={() => onSelect(cp)}
              className={`p-2.5 rounded border cursor-pointer transition ${
                selectedId === cp['config']['configurable']['checkpoint_id']
                  ? 'bg-blue-50/70 border-blue-400 text-blue-900 shadow-xs'
                  : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-600'
              }`}
            >
              <div className="flex justify-between font-bold mb-1">
                <span className={selectedId === cp.checkpoint_id ? 'text-blue-800' : 'text-slate-800'}>#{i} next: {cp.next}</span>
              </div>
                <span className="text-slate-400 font-normal shrink-0">{cp.created_at}</span>

              <div className="text-[10px] text-slate-400 truncate">ID: {cp['config']['configurable']['checkpoint_id']}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
