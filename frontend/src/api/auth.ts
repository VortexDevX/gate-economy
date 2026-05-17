import client from "./client";
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  PlayerResponse,
} from "./types";

export async function register(body: RegisterRequest): Promise<PlayerResponse> {
  const { data } = await client.post<PlayerResponse>("/auth/register", body);
  return data;
}

export async function login(body: LoginRequest): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>("/auth/login", body);
  return data;
}

export async function getMe(): Promise<PlayerResponse> {
  const { data } = await client.get<PlayerResponse>("/players/me");
  return data;
}
