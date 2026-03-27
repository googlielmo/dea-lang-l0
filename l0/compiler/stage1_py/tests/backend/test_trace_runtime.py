#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

import os

import pytest


@pytest.mark.skipif(os.name == "nt", reason="uses fork() to force child stderr ordering")
def test_trace_runtime_flushes_before_child_stderr(tmp_path, compile_and_run):
    c_code = r"""
    #define L0_TRACE_MEMORY 1
    #define SIPHASH_IMPLEMENTATION 1
    #include <sys/types.h>
    #include <sys/wait.h>
    #include <unistd.h>
    #include "l0_runtime.h"

    int main(void) {
        static char stderr_buf[4096];
        if (setvbuf(stderr, stderr_buf, _IOFBF, sizeof(stderr_buf)) != 0) {
            return 2;
        }

        _RT_TRACE_MEM("op=alloc_string len=%d ptr=%p", 1, (void*)0x1);

        pid_t pid = fork();
        if (pid < 0) {
            return 3;
        }
        if (pid == 0) {
            const char child_line[] = "child-stderr\n";
            write(2, child_line, sizeof(child_line) - 1);
            _exit(0);
        }

        int status = 0;
        if (waitpid(pid, &status, 0) < 0) {
            return 4;
        }
        if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
            return 5;
        }
        return 0;
    }
    """

    success, _stdout, stderr = compile_and_run(c_code, tmp_path)

    assert success, stderr
    lines = stderr.splitlines()
    assert len(lines) >= 2, stderr
    assert lines[0].startswith("[l0][mem] op=alloc_string len=1 ptr="), stderr
    assert lines[1] == "child-stderr", stderr
