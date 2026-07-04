import { useEffect, useRef, useState, useCallback } from 'react';
import { API_BASE_URL } from '../api';
/**
 * 通用原生 SSE 监听 Hook
 * @param {string | null} url 监听的流式接口地址，传 null 或空则不建立连接
 * @param {object} options 配置项 { enabled, onMessage, onError }
 */
export function useSSE({
    url = `${API_BASE_URL}/api/stream`,
    enabled = false,
    onMessage,
    onError
} = {}) {
    const [isConnected, setIsConnected] = useState(false);
    const sseRef = useRef(null);

    // 1. 手动关闭连接的方法
    const disconnect = useCallback(() => {
        if (sseRef.current) {
            sseRef.current.close();
            sseRef.current = null;
            setIsConnected(false);
            console.log('🔌 SSE 连接已优雅断开');
        }
    }, []);

    // 2. 核心连接逻辑
    useEffect(() => {
        // 只有当明确启用且 URL 存在时才建立连接
        if (!enabled || !url) {
            disconnect();
            return;
        }

        // 防止重复创建实例
        if (sseRef.current) return;

        console.log(`🌐 正在建立原生 SSE 连接: ${url}`);
        const es = new EventSource(url);
        sseRef.current = es;
        setIsConnected(true);

        es.onmessage = (event) => {
            if (!onMessage) return;
            try {
                const parsed = JSON.parse(event.data);
                onMessage(parsed);
            } catch {
                onMessage(event.data); // 非 JSON 格式退化为字符串
            }
        };

        es.onerror = (error) => {
            // 🎯 核心防错：检查当前原生事件源的状态
            const currentReadyState = es.readyState;

            // 场景 A：链接已经被关闭（后端顺利发完数据挂断，或者前端主动打断）
            if (currentReadyState === EventSource.CLOSED) {
                console.log('🏁 SSE 通道已安全闭合（正常结束或手动终止）');

                // 优雅收尾，不触发外层的崩溃回调 onError
                es.close();
                setIsConnected(false);
                sseRef.current = null;
                return;
            }

            // 场景 B：链接意外断开，浏览器正在原地自动尝试重连
            if (currentReadyState === EventSource.CONNECTING) {
                console.warn('⚠️ SSE 链接意外中断，浏览器正在尝试自动重连...');
                // 此时不需要彻底掐死（不调 es.close()），让原生爱继续自动重试
                return;
            }

            // 场景 C：真正的毁灭性服务异常（如后端奔溃、404、网关错误等）
            console.error('❌ SSE 管道发生实质性异常:', error);

            if (onError) {
                onError(error); // 只有这里才真正丢给外层组件去报错、切断开关
            }

            // 彻底销毁
            es.close();
            setIsConnected(false);
            sseRef.current = null;
        };


        // 🧹 当组件卸载、或开关关闭、或 URL 改变时，自动触发垃圾回收
        return () => {
            if (es) {
                es.close();
                setIsConnected(false);
                sseRef.current = null;
            }
        };
    }, [enabled]);

    return {
        isConnected,
        disconnect, // 暴露给前端做“强行打断”按钮
    };
}
