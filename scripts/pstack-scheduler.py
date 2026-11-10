#!/usr/bin/env python3
"""
CLI entrypoint wrapper for pstack_scheduler.py
"""
import sys
from pstack_scheduler import main

if __name__ == "__main__":
    sys.exit(main())
