class convert:
    def __init__(self, number):
        self.number = number
    def converterOctalToBits(self):
        unites = ['bits', 'Kbits', 'Mbits', 'Gbits', 'Tbits', 'Pbits', 'Ebits', 'Zbits', 'Ybits']
        i = 0
        n=self.number
        nbAConvertir=n*8
        while nbAConvertir >= 1000 and i < len(unites) - 1:
            nbAConvertir /= 1000.0
            i += 1
        return '{:.2f} {}'.format(nbAConvertir, unites[i])
    