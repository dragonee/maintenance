class Message:
    class Pressed:
        def __init__(self, value, long=False):
            self.button = value
            self.long = long

    @staticmethod
    def relay(relay1=False, relay2=False):
        return (int('0b00100000', 2) | (1 if relay1 else 0) | (2 if relay2 else 0)).to_bytes(1, 'little')

    @staticmethod
    def led(*args):
        val = 0

        for (i, b) in enumerate(args):
            val += b * 2**i

        return val.to_bytes(1, 'little')

    @classmethod
    def parse(cls, char):
        if char in (b'a', b'b', b'c'):
            return cls.Pressed(char)

        if char in (b'A', b'B', b'C'):
            return cls.Pressed(char, long=True)

        return None
