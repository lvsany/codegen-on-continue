import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import { store } from './redux/store';
import { VsCodeApiContext } from './context/VsCodeApi';
import { App } from './App';
import './index.css';

const vscode = acquireVsCodeApi();

function render() {
  // 多次尝试获取 root 元素
  let attempts = 0;
  const maxAttempts = 50;
  
  function tryRender() {
    const rootElement = document.getElementById('root');
    if (rootElement) {
      console.log('Root element found, rendering React app');
      ReactDOM.createRoot(rootElement).render(
        <React.StrictMode>
          <Provider store={store}>
            <VsCodeApiContext.Provider value={vscode}>
              <App />
            </VsCodeApiContext.Provider>
          </Provider>
        </React.StrictMode>
      );
    } else {
      attempts++;
      console.log(`Root element not found, attempt ${attempts}/${maxAttempts}`);
      if (attempts < maxAttempts) {
        setTimeout(tryRender, 100);
      } else {
        console.error('Root element not found after maximum attempts');
        // 作为最后的尝试，创建 root 元素
        const newRoot = document.createElement('div');
        newRoot.id = 'root';
        document.body.appendChild(newRoot);
        ReactDOM.createRoot(newRoot).render(
          <React.StrictMode>
            <Provider store={store}>
              <VsCodeApiContext.Provider value={vscode}>
                <App />
              </VsCodeApiContext.Provider>
            </Provider>
          </React.StrictMode>
        );
      }
    }
  }
  
  tryRender();
}

// 使用多种方式确保 DOM 准备好
if (document.readyState === 'complete') {
  render();
} else {
  window.addEventListener('load', render);
}
