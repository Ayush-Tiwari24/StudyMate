export const mockUser = {
  id: 1,
  name: 'Alex Rivera',
  email: 'alex@university.edu',
  preferences: {
    theme: 'light',
    top_k: 5,
    font_size: 'medium',
  },
  created_at: new Date().toISOString(),
};

export async function mockLogin(email, password) {
  await new Promise((r) => setTimeout(r, 300));
  return {
    data: {
      access_token: 'mock-jwt-token-studymate',
      refresh_token: 'mock-refresh-token',
      token_type: 'bearer',
      user: { ...mockUser, email },
    },
  };
}

export async function mockRegister(name, email, password) {
  await new Promise((r) => setTimeout(r, 400));
  return {
    data: {
      access_token: 'mock-jwt-token-studymate',
      refresh_token: 'mock-refresh-token',
      token_type: 'bearer',
      user: { ...mockUser, name, email },
    },
  };
}

export async function mockGetMe() {
  await new Promise((r) => setTimeout(r, 150));
  return { data: mockUser };
}
