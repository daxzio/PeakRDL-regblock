from ..lib.sim_testcase import SimTestCase
from ..lib.cpuifs.apb4 import APB4
from ..lib.cpuifs.obi import OBI
from ..lib.cpuifs.avalon import Avalon

class TestSimpleFanin_APB4(SimTestCase):
    cpuif = APB4()
    regwidth = 64
    n_regs = 4

    @classmethod
    def setUpClass(cls):
        cls.rdl_elab_params = {
            "N_REGS": cls.n_regs,
            "REGWIDTH": cls.regwidth,
        }
        super().setUpClass()

    def test_dut(self):
        self.run_test()

class TestSimpleFanin_OBI(SimTestCase):
    cpuif = OBI()
    regwidth = 64
    n_regs = 4

    @classmethod
    def setUpClass(cls):
        cls.rdl_elab_params = {
            "N_REGS": cls.n_regs,
            "REGWIDTH": cls.regwidth,
        }
        super().setUpClass()

    def test_dut(self):
        self.run_test()

class TestSimpleFanin_Avalon(SimTestCase):
    cpuif = Avalon()
    regwidth = 64
    n_regs = 4

    @classmethod
    def setUpClass(cls):
        cls.rdl_elab_params = {
            "N_REGS": cls.n_regs,
            "REGWIDTH": cls.regwidth,
        }
        super().setUpClass()

    def test_dut(self):
        self.run_test()
