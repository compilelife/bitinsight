from copy import copy
from abc import ABCMeta, abstractmethod
import math
import mmap

class BitPos:
    def __init__(self, byte_pos, bit_pos):
        self.byte = byte_pos
        self.bit = bit_pos

    def step(self):
        self.bit += 1
        if self.bit >= 8:
            self.byte += 1
            self.bit = 0

    def add(self, byte, bit):
        self.byte += byte
        self.bit += bit
        while self.bit >= 8:
            self.bit -= 8
            self.byte += 1

    def bits_to_bound(self):
        return 8 - self.bit

    def bits_count(self):
        return (self.byte << 3) + self.bit

    def __str__(self):
        return "(%d,%d)" % (self.byte, self.bit)


class BitStream:
    __metaclass__ = ABCMeta

    def __init__(self, mem):
        self._pos = BitPos(0, 0)
        self.bigendien = True
        self._end_pos = BitPos(len(mem), 0)
        self.mem = mem

    def pos(self):
        return copy(self._pos)

    def set_end_pos(self, byte, bit):
        self._end_pos.byte = byte
        self._end_pos.bit = bit

    def moveto(self, byte, bit):
        self._pos.byte = byte
        self._pos.bit = bit

    def skip(self, byte, bit = 0):
        self._pos.add(byte, bit)

    def eos(self):
        return self._pos.byte >= self._end_pos.byte
    
    def available(self):
        return self._end_pos.bits_count() - self._pos.bits_count()

    def __check_eos(self):
        if self.eos():
            raise EOFError()

    def read_bytes_to_str(self, count, forward=True):
        ret = self.read_bytes_to_array(count, forward)
        return ret.decode('utf-8')

    def read_bytes_to_array(self, count, forward=True):
        self.to_byte_end()
        e = None
        ret = bytearray()

        if not forward:
            pos = copy(self._pos)

        while count > 0:
            if self.eos():
                e = EOFError()
                break
            ret.append(self.mem[self._pos.byte])
            self._pos.byte += 1
            count -= 1

        if not forward:
            self._pos = pos

        if not e == None:
            raise e

        return ret

    def read_a_byte(self):
        self.to_byte_end()
        self.__check_eos()

        ret = self.mem[self._pos.byte]
        self._pos.byte += 1
        
        return ret

    def read_bytes(self, count, forward=True):
        ret = self.read_bytes_to_array(count, forward)
        return self.__to_number(ret)

    def read_a_bit(self):
        bit = ((self.mem[self._pos.byte] >> (8 - self._pos.bit - 1)) & 0x01)
        self._pos.step()
        return bit

    def read_bits_to_array(self, count, forward=True):
        bits = bytearray()
        e = None

        if not forward:
            pos = copy(self._pos)

        for i in range(count):
            if self.eos():
                e = EOFError()
                break
            bits.append(self.read_a_bit())

        if not forward:
            self._pos = pos

        if not e == None:
            raise e

        ret = bytearray()
        tail = count - int(math.floor(count/8)) * 8
        index = 0
        if tail > 0:
            b = 0
            for i in range(tail):
                b |= (bits[i] << (tail - i - 1))
            ret.append(b)
            index += tail

        while index < count:  # 剩下肯定是8的倍数了
            b = 0
            for i in range(8):
                b |= (bits[index+i] << (7 - i))
            ret.append(b)
            index += 8

        return ret

    def __to_number(self,arr):
        num=0
        size=len(arr)
        for i in range(size):
            if self.bigendien:
                num=(num << 8) | arr[i]
            else:
                num=(num << 8) | arr[size - i -1]
        return num

    def read_bits(self, count, forward=True):
        ret=self.read_bits_to_array(count, forward)
        return self.__to_number(ret)

    def read_bitss(self, count, times, forward=True):
        ret = []
        for i in range(times):
            ret.append(self.read_bits(count, forward))
        return ret

    def read_ue_golomb(self):
        i=0
        while not self.eos() and i < 32 and self.read_a_bit() == 0:
            i += 1
        ret=self.read_bits(i)
        ret += (1 << i)-1
        return ret

    def read_ue_golombs(self, count):
        ret=[]
        for i in range(count):
            ret.append(self.read_ue_golomb())
        return ret

    def read_se_golomb(self):
        ret=self.read_ue_golomb()
        if (ret & 0x01) > 0:
            ret=(ret + 1) / 2
        else:
            ret=-(ret/2)
        return ret

    def read_se_golombs(self, count):
        ret=[]
        for i in range(count):
            ret.append(self.read_se_golomb())
        return ret

    def to_byte_end(self):
        if self._pos.bit > 0:
            self._pos.byte += 1
            self._pos.bit=0