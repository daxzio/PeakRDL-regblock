from typing import List
import subprocess
import os
import shutil

from .base import Simulator

class Xilinx(Simulator):
    """
    Don't bother using the Xilinx simulator... Its buggy and extraordinarily slow.
    As observed in v2023.2:
        - clocking block assignments do not seem to actually simulate correctly.
          assignment statements get ignored or the values get mangled.
        - Streaming operators have all sorts of limitations.

    Keeping this here in case someday it works better...
    """
    name = "xilinx"

    @classmethod
    def is_installed(cls) -> bool:
        return (
            shutil.which("xvlog") is not None
            and shutil.which("xelab") is not None
            and shutil.which("xsim") is not None
        )

    def compile(self) -> None:
        cmd = [
            "xvlog", "--sv",
            "--log", "compile.log",
            "--include", os.path.join(os.path.dirname(__file__), ".."),
            "--define", "XSIM",
        ]
        cmd.extend(self.tb_files)
        subprocess.run(cmd, check=True)

        cmd = [
            "xelab",
            "--log", "elaborate.log",
            "--timescale", "1ns/1ps",
            "--debug", "all",
            "tb",
        ]
        subprocess.run(cmd, check=True)


    def run(self, plusargs:List[str] = None) -> None:
        plusargs = plusargs or []

        test_name = self.testcase.request.node.name

        # call vsim
        cmd = [
            "xsim",
            "--R",
            "--log", "%s.log" % test_name,
            "tb",
        ]

        for plusarg in plusargs:
            cmd.append("--testplusarg")
            cmd.append(plusarg)
        subprocess.run(cmd, check=True)

        self.assertSimLogPass("%s.log" % test_name)


    def assertSimLogPass(self, path: str):
        self.testcase.assertTrue(os.path.isfile(path))

        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("Error:"):
                    self.testcase.fail(line)
                elif line.startswith("Fatal:"):
                    self.testcase.fail(line)
                elif line.startswith("FATAL_ERROR:"):
                    self.testcase.fail(line)
