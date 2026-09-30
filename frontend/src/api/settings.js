/**
 * StudyMate RAG — Settings API Client
 */

import client from './client';

export const getSettings = () => client.get('/settings');

export const updateSettings = (data) => client.put('/settings', data);
