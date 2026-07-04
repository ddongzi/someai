export const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL) || 'http://localhost:8000';

const handleResponse = async (response) => {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
  }
  return response.json();
};

// 1. 获取当前状态
export const getState = async () => {
  const response = await fetch(`${API_BASE_URL}/api/state`);
  return handleResponse(response);
};

// 2. 启动工作流
export const startWorkflow = async () => {
  const response = await fetch(`${API_BASE_URL}/api/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse(response);
};

// 3. 获取历史记录
export const getHistory = async (limit = 20) => {
  const response = await fetch(`${API_BASE_URL}/api/history?limit=${limit}`);
  return handleResponse(response);
};

// 4. 重放指定的 Checkpoint
export const replay = async (checkpointId) => {
  const response = await fetch(`${API_BASE_URL}/api/replay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ checkpoint_id: checkpointId }),
  });
  return handleResponse(response);
};
export const continueWL = async () => {
  const response = await fetch(`${API_BASE_URL}/api/continue`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse(response);
}

// 5. 分叉指定的 Checkpoint
// 目前来看， fork只能从next 只有一个时候 fork
export const fork = async (checkpointId, state) => {
  const response = await fetch(`${API_BASE_URL}/api/fork`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ checkpoint_id: checkpointId, state }),
  });
  return handleResponse(response);
};

export const clear = async () => {
    const response = await fetch(`${API_BASE_URL}/api/clear`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse(response); 
}

export const interruptSubmit = async (checkpointId, interruptId, data) => {
  const response = await fetch(`${API_BASE_URL}/api/human_input`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ checkpoint_id: checkpointId, interrupt_id: interruptId, data }),
  });
  return handleResponse(response);
}