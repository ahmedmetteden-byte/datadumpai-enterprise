import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { RequestFeedbackHost } from '@/components/feedback';
import { AuthProvider } from '@/context/AuthContext';
import { RequestFeedbackProvider } from '@/context/RequestFeedbackContext';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <RequestFeedbackProvider>
        <AuthProvider>
          <App />
          <RequestFeedbackHost />
        </AuthProvider>
      </RequestFeedbackProvider>
    </BrowserRouter>
  </StrictMode>,
);
