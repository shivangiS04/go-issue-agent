"""Configuration module for Go Issue Agent."""
import os

# LLM Provider Configuration
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq")  # groq | anthropic | openai

# API Keys
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Model Configuration
GROQ_MODEL = "llama-3.3-70b-versatile"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
OPENAI_MODEL = "gpt-4o"

# Legacy support
GROQ_TEMPERATURE = 0.2

# Repository Configuration
APPROVED_REPOS = [
    ("spf13", "cobra"),
    ("gin-gonic", "gin"),
    ("go-playground", "validator"),
    ("golangci", "golangci-lint"),
]

# System Prompt for ALL LLM API calls
SYSTEM_PROMPT = (
    "You are a precise Go software engineer contributing to spf13/cobra, "
    "an open-source CLI library. You write minimal, correct Go code that "
    "matches the project's existing style. You always return valid JSON "
    "when asked for JSON. Never add markdown backticks around JSON output."
)

# Paths
OUTPUT_DIR = "./output"

# Retry Configuration
MAX_BUILD_RETRIES = 3
MAX_API_RETRIES = 3

# Search Configuration
MAX_RELEVANT_FILES = 4
MAX_FILE_LINES = 300
