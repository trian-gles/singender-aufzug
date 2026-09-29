#!/bin/bash
/home/pi/llama.cpp/build/bin/llama-server -m /home/pi/singender-aufzug/models/llm/Qwen3-4B-Q4_K_M.gguf --host 127.0.0.1 --port 8080 -c 2048 -v
