sigaedu_scraper
---------------

**PS: É importante executar todos os comandos na sequência mostrada abaixo, devido ao modo como o sistema funciona.**

Para obter as notas de uma matéria:

.. code-block:: python

    >>> import sigaedu_scraper
    >>> scraper = sigaedu_scraper.Scraper('usuario', 'senha', 'https://sigaedu.example.com/', 'identificador_da_sua_aplicacao')
    >>> matriculas = scraper.get_matriculas()
    >>> matriculas
    {
        1: '2016071099999-1 AAA - NOME DO CURSO'
    }
    >>> periodos = scraper.get_periodos(1)
    >>> periodos
    {
        1: '01/02/2016 - 01/12/2016',
        2: '01/02/2017 - 01/12/2017',
        ...
    }
    >>> diario = scraper.get_diario(1)
    >>> diario.get_disciplinas()
    [
        <Disciplina 'GEOGRAFIA'>,
        <Disciplina 'ALGORITMOS'>,
        ...
    ]
    >>> geo = diario.get_disciplina('GEOGRAFIA')
    >>> geo.nome
    'GEOGRAFIA'
    >>> geo.notas
    {
        'Bimestre 1': 10.0,
        'Rec. Parcial 1': 0.0,
        ...
    }
    >>> geo.get_medias()
    [10.0, 9.0, 9.0, 10.0]
