import pandas as pd

from data import categoria_risco


class TestCategoriaRisco:
    def test_sentinel_sem_dado(self):
        assert categoria_risco(-999) == "Sem dado"

    def test_nan_sem_dado(self):
        assert categoria_risco(float("nan")) == "Sem dado"

    def test_limites(self):
        assert categoria_risco(0) == "Baixo"
        assert categoria_risco(25) == "Baixo"
        assert categoria_risco(26) == "Médio"
        assert categoria_risco(50) == "Médio"
        assert categoria_risco(51) == "Alto"
        assert categoria_risco(75) == "Alto"
        assert categoria_risco(76) == "Crítico"
        assert categoria_risco(100) == "Crítico"
