interface Config {
  apiBaseUrl: string
}

function loadConfig(): Config {
  return {
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  }
}

export const config = loadConfig()
