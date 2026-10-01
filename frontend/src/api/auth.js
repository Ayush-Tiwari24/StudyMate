import client from './client';
import { mockLogin, mockRegister, mockGetMe } from './mock/auth';

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export const register = (name, email, password) => {
  if (USE_MOCK) return mockRegister(name, email, password);
  return client.post('/auth/register', { name, email, password });
};

export const login = (email, password) => {
  if (USE_MOCK) return mockLogin(email, password);
  return client.post('/auth/login', { email, password });
};

export const getMe = () => {
  if (USE_MOCK) return mockGetMe();
  return client.get('/auth/me');
};

export const deleteAccount = (password) => {
  return client.delete('/auth/me', { data: { password } });
};

export const exportUserData = () => {
  return client.get('/auth/me/export');
};


