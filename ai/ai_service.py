"""
AI Service - Abstraction layer for Ollama, OpenAI, and Anthropic
"""

import json
import logging
import threading
import requests
from typing import Optional, Callable, Generator
from config.settings import get_setting, set_setting, decrypt_value

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# BASE PROVIDER
# ─────────────────────────────────────────────

class AIProvider:
    name = "base"

    def is_available(self) -> bool:
        raise NotImplementedError

    def chat(self, messages: list, stream_cb: Optional[Callable[[str], None]] = None) -> str:
        raise NotImplementedError

    def list_models(self) -> list:
        return []


# ─────────────────────────────────────────────
# OLLAMA PROVIDER
# ─────────────────────────────────────────────

class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:1.5b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if r.status_code == 200:
                data = r.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"list_models error: {e}")
        return []

    def chat(self, messages: list, stream_cb: Optional[Callable[[str], None]] = None) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream_cb is not None,
        }
        try:
            if stream_cb:
                return self._stream(payload, stream_cb)
            else:
                r = requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=120,
                )
                r.raise_for_status()
                return r.json()["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            return f"[Ollama Error] {e}"

    def _stream(self, payload: dict, stream_cb: Callable[[str], None]) -> str:
        full_response = ""
        try:
            with requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        full_response += token
                        stream_cb(token)
                        if chunk.get("done"):
                            break
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            full_response = f"[Stream Error] {e}"
        return full_response

    def pull_model(self, model_name: str, progress_cb: Optional[Callable[[str, int], None]] = None) -> bool:
        """Pull a model from Ollama registry with optional progress callback."""
        try:
            with requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                stream=True,
                timeout=600,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        status = data.get("status", "")
                        total = data.get("total", 0)
                        completed = data.get("completed", 0)
                        pct = int((completed / total) * 100) if total > 0 else 0
                        if progress_cb:
                            progress_cb(status, pct)
                        if status == "success":
                            return True
        except Exception as e:
            logger.error(f"pull_model error: {e}")
        return False

    def delete_model(self, model_name: str) -> bool:
        try:
            r = requests.delete(f"{self.base_url}/api/delete", json={"name": model_name}, timeout=10)
            return r.status_code == 200
        except Exception as e:
            logger.error(f"delete_model error: {e}")
            return False


# ─────────────────────────────────────────────
# OPENAI PROVIDER
# ─────────────────────────────────────────────

class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def is_available(self) -> bool:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            client.models.list()
            return True
        except Exception:
            return False

    def chat(self, messages: list, stream_cb: Optional[Callable[[str], None]] = None) -> str:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            if stream_cb:
                full = ""
                with client.chat.completions.create(
                    model=self.model, messages=messages, stream=True
                ) as stream:
                    for chunk in stream:
                        token = chunk.choices[0].delta.content or ""
                        full += token
                        stream_cb(token)
                return full
            else:
                resp = client.chat.completions.create(model=self.model, messages=messages)
                return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            return f"[OpenAI Error] {e}"


# ─────────────────────────────────────────────
# ANTHROPIC PROVIDER
# ─────────────────────────────────────────────

class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.api_key = api_key
        self.model = model

    def is_available(self) -> bool:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False

    def chat(self, messages: list, stream_cb: Optional[Callable[[str], None]] = None) -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            system_msgs = [m["content"] for m in messages if m["role"] == "system"]
            chat_msgs = [m for m in messages if m["role"] != "system"]
            system = system_msgs[0] if system_msgs else None

            kwargs = dict(model=self.model, max_tokens=2048, messages=chat_msgs)
            if system:
                kwargs["system"] = system

            if stream_cb:
                full = ""
                with client.messages.stream(**kwargs) as stream:
                    for text in stream.text_stream:
                        full += text
                        stream_cb(text)
                return full
            else:
                resp = client.messages.create(**kwargs)
                return resp.content[0].text
        except Exception as e:
            logger.error(f"Anthropic chat error: {e}")
            return f"[Anthropic Error] {e}"


# ─────────────────────────────────────────────
# AI SERVICE (Singleton manager)
# ─────────────────────────────────────────────

class AIService:
    """
    Central AI service. Selects provider based on settings.
    Gracefully handles no-AI mode.
    """
    _instance = None

    def __init__(self):
        self._provider: Optional[AIProvider] = None
        self._lock = threading.Lock()
        self._system_prompt = (
            "You are an intelligent PC optimization assistant. "
            "You help users understand their system performance, "
            "suggest safe cleanup steps, explain technical concepts clearly, "
            "and provide actionable recommendations. Be concise and friendly."
        )
        self.reload()

    @classmethod
    def get_instance(cls) -> "AIService":
        if cls._instance is None:
            cls._instance = AIService()
        return cls._instance

    def reload(self):
        """Reload provider from current settings."""
        with self._lock:
            provider_name = get_setting("ai_provider", "none")
            if provider_name == "ollama":
                url = get_setting("ollama_url", "http://localhost:11434")
                model = get_setting("ollama_model", "qwen2.5:1.5b")
                self._provider = OllamaProvider(base_url=url, model=model)
            elif provider_name == "openai":
                key = decrypt_value(get_setting("openai_key_enc", ""))
                self._provider = OpenAIProvider(api_key=key)
            elif provider_name == "anthropic":
                key = decrypt_value(get_setting("anthropic_key_enc", ""))
                self._provider = AnthropicProvider(api_key=key)
            else:
                self._provider = None
            logger.info(f"AIService loaded provider: {provider_name}")

    @property
    def provider(self) -> Optional[AIProvider]:
        return self._provider

    @property
    def is_configured(self) -> bool:
        return self._provider is not None

    @property
    def is_available(self) -> bool:
        if self._provider is None:
            return False
        return self._provider.is_available()

    @property
    def provider_name(self) -> str:
        if self._provider:
            return self._provider.name
        return "none"

    def chat(
        self,
        user_message: str,
        history: list = None,
        stream_cb: Optional[Callable[[str], None]] = None,
        context: str = None,
    ) -> str:
        """
        Send a message. Returns full response string.
        Optionally streams tokens via stream_cb.
        """
        if not self.is_configured:
            return "AI assistant is not configured. Go to Settings → AI Configuration to set it up."

        messages = [{"role": "system", "content": self._system_prompt}]
        if context:
            messages[0]["content"] += f"\n\nCurrent System Context:\n{context}"
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        with self._lock:
            return self._provider.chat(messages, stream_cb=stream_cb)

    def get_optimization_suggestions(self, metrics_summary: str) -> str:
        """Ask AI for optimization suggestions based on metrics."""
        prompt = (
            f"Based on these current system metrics:\n{metrics_summary}\n\n"
            "Provide 3-5 specific, actionable optimization suggestions. "
            "Be brief and practical. Format as a numbered list."
        )
        return self.chat(prompt)


# ─────────────────────────────────────────────
# OLLAMA INSTALLER
# ─────────────────────────────────────────────

class OllamaInstaller:
    """Handles Ollama detection, download, and installation."""

    OLLAMA_API_RELEASE = "https://api.github.com/repos/ollama/ollama/releases/latest"
    OLLAMA_DOWNLOAD_BASE = "https://github.com/ollama/ollama/releases/latest/download"

    @staticmethod
    def is_installed() -> bool:
        import subprocess
        try:
            result = subprocess.run(["ollama", "--version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False

    @staticmethod
    def is_running() -> bool:
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    @staticmethod
    def start_service() -> bool:
        import subprocess
        try:
            subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NO_WINDOW)
            import time; time.sleep(3)
            return OllamaInstaller.is_running()
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            return False

    @staticmethod
    def download_installer(
        dest_path: str,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """Download OllamaSetup.exe from GitHub."""
        url = f"{OllamaInstaller.OLLAMA_DOWNLOAD_BASE}/OllamaSetup.exe"
        try:
            r = requests.get(url, stream=True, timeout=30)
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total and progress_cb:
                        progress_cb(int((downloaded / total) * 100))
            return True
        except Exception as e:
            logger.error(f"Ollama download error: {e}")
            return False

    @staticmethod
    def install_from_exe(exe_path: str) -> bool:
        import subprocess
        try:
            result = subprocess.run(
                [exe_path, "/S"],  # Silent install
                timeout=120,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Ollama install error: {e}")
            return False

    @staticmethod
    def select_model(ram_gb: float, has_gpu: bool) -> str:
        """Auto-select best model based on hardware."""
        if has_gpu:
            return "gemma2:2b"
        if ram_gb < 8:
            return "phi3:mini"
        return "qwen2.5:1.5b"

    @staticmethod
    def detect_gpu() -> bool:
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, timeout=5
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            return False

    @staticmethod
    def get_ram_gb() -> float:
        import psutil
        return psutil.virtual_memory().total / 1e9
