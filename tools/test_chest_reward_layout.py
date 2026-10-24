"""Execute reward bridges with hostile callees and inspect pre-queue item text."""
import unittest
from capstone import Cs,CS_ARCH_PPC,CS_MODE_64,CS_MODE_BIG_ENDIAN
from check_translation import ROOT
import chest_reward_layout as layout
from test_inventory_layout import InventoryMachine,MASK64

RESOLVER=0x448098
TABLE=0x55c0000
ALIASES=0x55d1000


class RewardMachine(InventoryMachine):
    def __init__(self,item,target):
        super().__init__(lambda size:0)
        self.start=0x449000
        payload=layout.bridge(self.start,RESOLVER,TABLE,2,ALIASES,27,target)
        md=Cs(CS_ARCH_PPC,CS_MODE_64|CS_MODE_BIG_ENDIAN)
        self.instructions={i.address:(i.mnemonic,i.op_str) for i in md.disasm(payload,self.start)}
        self.asserted_item=item;self.target=target;self.shown=None
        self._write(self.initial_regs[5],b'~T00000000~+2\0')

    def _store(self,address,value,size=8):
        if not self.stack_start-layout.FRAME<=address<self.stack_start:
            raise AssertionError('Reward bridge wrote outside its own frame')
        self._write(address,(value&((1<<(size*8))-1)).to_bytes(size,'big'))

    def _native_call(self,target,return_address):
        self.calls.append(target)
        if target==RESOLVER:
            expected=[self.initial_regs[5],self.regs[1]+layout.BUFFER,layout.CAPACITY,
                      TABLE,2,ALIASES,27]
            if self.regs[3:10]!=expected:raise AssertionError('Wrong resolver ABI')
            self._write(self.regs[4],self.asserted_item+b'\0')
            result=self.regs[4]
        elif target==self.target:
            expected=self.initial_regs[3:13].copy();expected[2]=self.regs[1]+layout.BUFFER
            if self.regs[3:13]!=expected:raise AssertionError('Original message arguments lost')
            if (self.fprs[1:14]!=self.initial_fprs[1:14] or self.cr!=self.initial_cr
                    or self.ctr!=self.initial_ctr):raise AssertionError('Vararg state lost')
            pointer=self.regs[5];data=bytearray()
            while self.memory[pointer]:data.append(self.memory[pointer]);pointer+=1
            self.shown=bytes(data)
            result=self.draw_result
        else:raise AssertionError('Unexpected native call')
        # ELFv1 callees may spill in the linkage/parameter area; all bridge
        # locals must survive even its conservative full +0xf8 overwrite.
        for offset in range(0x10,0x100,8):self._store(self.regs[1]+offset,0xbad+offset)
        for r in [0,2]+list(range(3,13)):self.regs[r]=0xdead000+r
        for r in range(14):self.fprs[r]=0xbadf0000+r
        self.regs[3]=result
        self.cr,self.ctr,self.lr=0x12345678,0xbadc0ffee,return_address

    def _result(self):
        if (self.regs[1]!=self.initial_regs[1] or self.regs[2]!=self.initial_regs[2]
                or self.regs[4:]!=self.initial_regs[4:] or self.regs[3]!=self.draw_result
                or self.fprs[1:14]!=self.initial_fprs[1:14] or self.cr!=self.initial_cr
                or self.ctr!=self.initial_ctr or self.lr!=self.initial_lr):
            raise AssertionError('Reward bridge failed to preserve native state')
        if bytes(self.memory[self.stack_start+i] for i in range(len(self.caller_before)))!=self.caller_before:
            raise AssertionError('Reward bridge overwrote its caller')
        if self.calls!=[RESOLVER,self.target]:raise AssertionError('Wrong call order')
        return self.shown


class ChestRewardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()

    def test_names_are_expanded_before_both_native_message_queues(self):
        for item in (b'Item',b'Item+2',b'Healing Salve Concentrate',
                     b'Cremation Scripture Scroll',b'Long Sword-16',b'x'*1000):
            for _,target in layout.SITES:
                with self.subTest(item=item[:40],target=hex(target)):
                    self.assertEqual(RewardMachine(item,target).run(),item)

    def test_scope_guards_and_native_wait_remain_intact(self):
        code=bytearray();changes,audit=layout.append_code(self.original,code,RESOLVER,TABLE,2,ALIASES,27)
        self.assertEqual([a+0x10000 for a,_ in changes],[a for a,_ in layout.SITES])
        self.assertTrue(audit['expands_before_native_message_formatting'])
        self.assertFalse(audit['shared_mutable_storage'])
        self.assertLess(audit['buffer_offset']+audit['capacity'],audit['frame_bytes'])
        for a,h in layout.GUARDS:
            for n in range(0,len(bytes.fromhex(h)),4):
                original=bytearray(self.original);original[a-0x10000+n]^=1;code=bytearray()
                with self.assertRaises(ValueError):layout.append_code(original,code,RESOLVER,TABLE,2,ALIASES,27)
                self.assertFalse(code)


if __name__=='__main__':unittest.main()
