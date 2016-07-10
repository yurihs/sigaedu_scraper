#!/usr/bin/env python3

import logging

import requests
import requests.compat
from lxml import html


class LoginError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Disciplina:
    """
    Disciplina de um diário do SIGA-EDU
    Processa dados relacionados à uma disciplina, facilita o acesso aos mesmos

    Métodos:
        get_medias: Obtém as médias bimestrais ou trimestrais da disciplina
    """
    def __init__(self, nome: str, notas: list, media_final: float, status: str):
        self.nome = nome
        self.notas = self._processar_notas(notas)
        self.media_final = media_final
        self.status = status

    @staticmethod
    def _processar_notas(raw_notas: list) -> dict:
        """
        Transforma as notas em tuplas, separando o nome do valor

        Retorna:
            Uma dicionário de notas, contendo o nome da nota e o seu valor
        Exemplos:
            {'Bimestre 1': 8.5, 'Bimestre 2': 8.0}
            {'1º trimestre': 8.5}
        """
        notas = {}
        for nota in raw_notas:
            n_hifens = nota.count(' - ')
            if n_hifens == 2:
                # Exemplo: 1 - 1 Bimestre - Média: 8.5
                nome, valor = nota.replace('Média: ', '').split(' - ')[1:]  # Elimina o primeiro número
                nota = (nome, float(valor))  # Transforma o valor da nota em float
            elif n_hifens == 1:
                # Exemplo: 1º trimestre - Média: 8.5
                nome, valor = nota.replace('Média: ', '').split(' - ')
                nota = (nome, float(valor))
            else:
                nota = (nota, None)
            notas.update([nota])

        return notas

    def get_medias(self) -> list:
        """
        Normaliza as médias bimestrais ou trimestrais da disciplina
        A detecção da bimestralidade ou trimestralidade é feita pelo nome das notas

        Retorna:
            Uma lista contendo as médias encontradas, preenchida por None as que faltam
        Exemplos:
            Bimestral:
                [7.0, 8.0, 9.0, None]
                [8.0, 9.0, 8.5, 7.0]
            Trimestral:
                [6.0, 8.0, 8.2]
                [None, None, None]
        """
        # Notas que tem 'bimestre' e 'trimestre' em seus nomes
        bimestres = {k: v for k, v in self.notas.items() if 'bimestre' in k.lower()}
        trimestres = {k: v for k, v in self.notas.items() if 'trimestre' in k.lower()}

        # Disciplinas bimestrais terão 0 notas trimestrais, e vice-versa
        if len(bimestres) > len(trimestres):
            # É bimestral
            return list(bimestres.values()) + [None]*(4-len(bimestres))
        elif len(trimestres) > len(bimestres):
            # É trimestral
            return list(trimestres.values()) + [None]*(3-len(trimestres))
        else:
            # Indefinido
            return None

    def __str__(self) -> str:
        return self.nome

    def __repr__(self) -> str:
        return '<Disciplina \'{0}\'>'.format(self.nome)


class Diario:
    """
    Diário do SIGA-EDU
    Facilita o acesso às disciplinas

    Métodos:
        get_disciplinas: Lista de todas as disciplinas
        get_disciplina: Obter uma disciplina pelo nome
        del_disciplina: Remover uma disciplina pelo nome
        add_disciplina: Adicionar uma disciplina

    """
    def __init__(self):
        self.disciplinas = set()

    def get_disciplinas(self) -> list:
        """
        Obtém a lista de todas as disciplinas
        """
        return list(self.disciplinas)

    def get_disciplina(self, nome: str) -> Disciplina:
        """
        Obtém uma disciplina pelo nome

        Retorna:
            A disciplina caso for encontrada
            None caso não for
        """
        for disciplina in self.disciplinas:
            if disciplina.nome == nome:
                return disciplina

    def add_disciplina(self, disciplina: Disciplina):
        """
        Adiciona uma disciplina pelo nome
        """
        self.disciplinas.add(disciplina)

    def del_disciplina(self, nome: str):
        """
        Remove uma disciplina pelo nome
        """
        for i, disciplina in enumerate(self.disciplinas):
            if disciplina.nome == nome:
                self.disciplinas.remove(disciplina)

    def __str__(self) -> str:
        return str(self.disciplinas)

    def __repr__(self) -> str:
        return '<Diário com {0} disciplinas>'.format(len(self.disciplinas))


class Session:
    """
    Sessão do SIGA-EDU

    Possibilita a autenticação e a realização de requests a um sistema SIGA-EDU
    Gerencia o ID de sessão e o parâmetro viewstate do sistema JSF

    Métodos:
        do_post_request: Realiza um pedido
        get_id: Obtém o ID de sessão atual

    """
    def __init__(self, user: str, password: str, url: str, user_agent: str):
        self.url = url  # Página base
        self.viewstate = None  # Viewstate inicial é desconhecido

        # Inicia a sessão
        self.session = requests.Session()
        if user_agent:
            self.session.headers.update({
                'User-Agent': user_agent
            })

        # Faz login
        self.login(user, password)
        logging.debug("Sessão '{0}' inicializada".format(self.get_id()))

    def do_post_request(self, page: str, *args: list, **kwargs: dict) -> requests.Request():
        """
        Realiza um pedido HTTP do tipo POST para a página fornecida, com os argumentos fornecidos

        Retorna:
            O pedido já executado
        """
        # Cria o parâmetro 'data' nos kwargs caso não seja fornecido
        if 'data' not in kwargs.keys():
            kwargs['data'] = {}

        # Adiciona o parâmetro viewstate atual aos dados do request
        kwargs['data'].update({
            'javax.faces.ViewState': self.viewstate
        })

        logging.debug("Fazendo um pedido para '{0}' com o viewstate '{1}'".format(page, self.viewstate))
        # Faz o pedido, passando os argumentos recebidos
        req = self.session.post(requests.compat.urljoin(self.url, page), *args, **kwargs)

        # Atualiza o viewstate
        self.viewstate = self._get_viewstate_from_request(req)

        return req

    def login(self, user: str, password: str) -> bool:
        """
        Acessa a pagina de login e envia o usuario e senha, autenticado o usuário

        Retorna:
            Verdadeiro caso o login foi feito corretamente
        """
        pagina_login = '/login.jsf'

        # Ir à página de login, gerando o cookie com um ID de sessão
        self.do_post_request(pagina_login)

        # Dados submetidos com o formulário
        data = {
            'formlogin': 'formlogin',
            'formlogin:login': user,
            'formlogin:senha': password,
            'formlogin:botaologar': 'Entrar'
        }

        # Submete os dados e interpreta a resposta
        req = self.do_post_request(pagina_login, data=data)
        tree = html.fromstring(req.content)

        # Verifica se um erro foi mostrado
        erros = tree.xpath('//div[@class="error"]')
        if erros:
            e = LoginError('Erro ao fazer login com o usuario {0}'.format(user))
            raise e

    def get_id(self) -> str:
        """
        Obtem o ID da sessão atual por meio do cookie

        Retorna:
            O ID caso esteja presente
            None caso não esteja
        """
        if self.session:
            return self.session.cookies.get('JSESSIONID')
        else:
            return None

    @staticmethod
    def _get_viewstate_from_request(req: requests.Request()) -> str:
        """
        Obtem o parametro "javax.faces.ViewState" da aplicação por meio de um elemento input presente na página

        Retorna:
            O viewstate caso esteja presente
            None caso não esteja
        """
        tree = html.fromstring(req.content)
        # Procura o valor do primeiro elemento <input type="hidden" id="javax.faces.ViewState">
        viewstates = tree.xpath('(//input[@id="javax.faces.ViewState"])[1]/@value')
        if len(viewstates) == 0:
            return None
        else:
            return viewstates[0]

    def __str__(self) -> str:
        return self.get_id()

    def __repr__(self) -> str:
        return '<SIGA-EDU Session \'{0}\'>'.format(self.get_id())


class Scraper:
    """
    Scraper do SIGA-EDU
    Realiza a extração de dados referentes às matriculas, períodos, diários e disciplinas a partir de uma sessão

    Métodos:
        get_matriculas
        get_periodos
        get_diario
    """
    def __init__(self, user: str, password: str, url: str, user_agent: str = None):
        self.session = Session(user, password, url, user_agent)

    def get_matriculas(self) -> dict:
        """
        Obtém a lista de matrículas por meio do dropdown de matrículas

        Retorna:
            Dicionário com IDs e nomes das matrículas
        """
        pagina_inicial = '/sigaept-edu-web-v1/pages/inicial.jsf'  # Página inicial que contém o menu lateral
        # Dados para acessar a lista de matrículas por meio do botão no menu lateral
        dados_pagina_matriculas = {
            'menuLateralSiga': 'menuLateralSiga',
            'menuLateralSiga:listaMenu:1:listaCDUFilho:0:_': 'menuLateralSiga:listaMenu:1:listaCDUFilho:0:_'
        }

        req = self.session.do_post_request(pagina_inicial, data=dados_pagina_matriculas)
        tree = html.fromstring(req.content)

        # Acha as opções (valores e textos) do dropdown <select id="busca:matriculas">
        matriculas_valores = tree.xpath('//*[@id="busca:matriculas"]/option/@value')
        matriculas_nomes = tree.xpath('//*[@id="busca:matriculas"]/option/text()')

        # Junta os valores (IDs) e textos (descrições) em um dict
        matriculas = {
            int(x[0]): x[1]
            for x in zip(matriculas_valores, matriculas_nomes)
            if x[1] != 'Selecione um número de matrícula!'  # Exclui a opção padrão
        }

        return matriculas

    def get_periodos(self, id_matricula: int) -> dict:
        """
        Obtém a lista de períodos por meio do dropdown de períodos em uma matricula

        Retorna:
            Dicionário com IDs e nomes dos períodos
        """
        pagina_periodos = '/sigaept-edu-web-v1/pages/AlunoVisualizarNotas/AlunoVisualizarMatricula.jsf'
        dados = {
            'busca': 'busca',
            'busca:matriculas': id_matricula,
            'busca:j_id73': 'Avançar'
        }

        req = self.session.do_post_request(pagina_periodos, data=dados)
        tree = html.fromstring(req.content)

        # Acha as opções (valores e textos) do dropdown <select id="busca:periodoLetivo">
        periodos_valores = tree.xpath('//*[@id="busca:periodoLetivo"]/option/@value')
        periodos_nomes = tree.xpath('//*[@id="busca:periodoLetivo"]/option/text()')

        # Junta os valores (IDs) e textos (descrições) em um dict
        periodos = {
            int(x[0]): x[1]
            for x in zip(periodos_valores, periodos_nomes)
            if x[1] != 'Selecione um período letivo'  # Exclui a opção padrãp
        }

        return periodos

    def get_diario(self, id_periodo: int) -> Diario:
        """
        Obtém um diário (com as disciplinas) de um período.
        A matéria deve ser escolhida antes, por meio do método get_periodos()

        Retorna:
           Um objeto diário
        """
        pagina_diario = '/sigaept-edu-web-v1/pages/AlunoVisualizarNotas/AlunoVisualizarInformacoesDiario.jsf'
        dados = {
            'AJAXREQUEST': '_viewRoot',
            'busca': 'busca',
            'busca:periodoLetivo': id_periodo,
            'busca:classes:j_id78fsp': '',
            'busca:classes:j_id81fsp': '',
            'busca:j_id74': 'busca:j_id74',
            '': ''
        }

        req = self.session.do_post_request(pagina_diario, data=dados)
        tree = html.fromstring(req.content)

        # Obtém as disciplinas de cada linha da tabela
        raw_disciplinas = tree.xpath('//table/tbody[@id="busca:classes:tb"]/tr')
        diario = Diario()

        for disciplina in raw_disciplinas:
            # Extrai o nome da primeira coluna, elimina números no começo e a última letra
            nome = disciplina.xpath('td[1]/text()')[0][14:-1]
            # Extrai as notas da terceira coluna, remove os caracteres no final
            notas = list(map(str.strip, disciplina.xpath('td[3]/div/div/text()')))
            # Extrai a media final e o status da quarta e sexta coluna, respectivamente, e remove os caracteres no final
            media_final = float(disciplina.xpath('td[4]/label/text()')[0].strip())
            status = disciplina.xpath('td[6]/text()')[0].strip()

            # Inicializa o objeto Disciplina com os valores extraidos, adiciona ao diario
            diario.add_disciplina(Disciplina(nome, notas, media_final, status))

        return diario
