from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import os
import pandas as pd
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from datetime import datetime
import hashlib
import re
from sqlalchemy import create_engine
import getpass
from sqlalchemy import text
from flask_sqlalchemy import SQLAlchemy
from flask import session
import tempfile
from flask import current_app
import logging
from flask import send_file
import io


# Importações necessárias para manipulação de PDF e fontes
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.units import cm

# Inicialização do Flask
app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'

# Configuração do SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://usuario:senha@host/banco'
app.secret_key = 'confidencial'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)  # Inicialize o db corretamente aqui

# Função para carregar dados do PostgreSQL
def carregar_dados_postgresql():
    query_view = """
        SELECT cod_imovel, nom_municipio, nom_imovel, nome_prop, dt_validacao, condicao_analise, 
               num_area_imovel, ind_status_imovel, ind_tipo_imovel, cd_mun, cod_protocolo, status_validacao
        FROM visoes.mvw_base_aplicativo_certificados;
    """
    df = pd.read_sql(query_view, db.engine)
    return df

# Adicionar verificação de valores nulos e inconsistentes antes de gerar certificados
def verificar_consistencia_dados(df):
    colunas_criticas = ['cod_imovel', 'nom_municipio', 'nome_prop', 'cd_mun', 'num_area_imovel', 'dt_validacao']
    inconsistencias = df[colunas_criticas].isnull().sum()
    inconsistentes = inconsistencias[inconsistencias > 0]
    if not inconsistentes.empty:
        logging.warning(f"Inconsistências encontradas nas colunas: {inconsistentes.to_dict()}")
    
    if not pd.api.types.is_numeric_dtype(df['num_area_imovel']):
        logging.error("A coluna 'num_area_imovel' contém valores não numéricos.")
    
    return df

# Função para validar o formato RECIBO CAR
def validar_formato_codigo(codigo):
    # Regex para o formato PA-1500909-D022BC6352C94251B34E123738F02916
    padrao = re.compile(r'^[A-Z]{2}-\d{7}-[A-Z0-9]{32}$')
    return bool(padrao.match(codigo))

#Configuração do SQLAlchemy
from flask_sqlalchemy import SQLAlchemy

# Definir o caminho base dos arquivos emitidos
caminho_base_certificados = "C:/exemplo/CERTIFICADOS EMITIDOS"

# Função para criar o arquivo modelo
def criar_arquivo_modelo():
    caminho_pasta = r'C:/exemplo/BASES PARA GERAÇÃO DE CERTIFICADOS'
    arquivo_modelo = os.path.join(caminho_pasta, 'LAYOUTS/Cadastros a certificar.xlsx')
    return arquivo_modelo

# Carregar dados do PostgreSQL uma única vez no contexto do app
with app.app_context():
    df_sicar = carregar_dados_postgresql()

# Função para gerar um código numérico a partir do texto
def gerar_codigo_numero(texto):
    return int(hashlib.md5(str(texto).encode()).hexdigest(), 16) % (10 ** 5)

# Função para extrair "NOME_AST" de nom_imovel
def extrair_nome_ast(nom_imovel):
    try:
        return nom_imovel.split('- ')[1].split(' -')[0].upper()
    except IndexError:
        return ""

# Função para extrair "LOTE_AST" de nom_imovel
def extrair_lote_ast(nom_imovel):
    try:
        lotes = re.findall(r'LOTE\s+(\d+[A-Z]?)', nom_imovel, re.IGNORECASE)
        return ', '.join(lotes)
    except AttributeError:
        return ""

# Função para criar a enumeração temporária para "LOTE_AST"
def criar_enumeracao_lote_ast(df):
    def parse_lote(lote):
        match = re.match(r'(\d+)([A-Z]?)', lote)
        if match:
            num = int(match.group(1))
            suffix = match.group(2)
            return num * 100 + (ord(suffix) - ord('A') + 1 if suffix else 0)
        return 0

    df_temp = df.copy()
    df_temp['lote_enum'] = df_temp['lote_ast'].apply(lambda x: min([parse_lote(l) for l in x.split(', ')]))
    df_temp = df_temp.sort_values(by=['nome_ast', 'lote_enum'])
    df_temp['temp_enum'] = range(1, len(df_temp) + 1)
    
    return df_temp[['cod_imovel', 'temp_enum']]

# Função para remover qualquer variação de "INSTITUTO" de nome_prop
def limpar_nome_prop(nome_prop):
    partes = nome_prop.split(',')
    partes = [parte.strip() for parte in partes if not parte.strip().upper().startswith("INSTITUTO")]
    return ', '.join(partes)

# Função para converter número em ordinal
def ordinal(n):
    return "%d%s" % (n, "º" if 10 <= n % 100 < 20 else {1: "ª", 2: "ª", 3: "ª"}.get(n % 10, "ª"))

def verificar_casos_adversos(df):
    # Filtrar os registros de acordo com diferentes condições adversas
    validado_car20 = df[df['status_validacao'] == "Validado pelo CAR 2.0"]
    nao_validado = df[df['status_validacao'] == "Não Validado"]
    cancelados = df[df['ind_status_imovel'] == 'CA']
    suspensos = df[df['ind_status_imovel'] == 'SU']
    pendentes_validado = df[(df['status_validacao'] == "Validado") & (df['ind_status_imovel'] == "PE")]

    # Retornar os DataFrames filtrados
    return validado_car20, nao_validado, cancelados, suspensos, pendentes_validado

import pandas as pd
from datetime import datetime
import getpass

#1 Gerar o DataFrame de Metadados
#1 Gerar o DataFrame de Metadados
def gerar_dataframe_metadados(df, tipo_certificado, lote_geracao, tentativa_suspensos, tentativa_cancelados):
    # Obtenha o número de geração sequencial
    numero_geracao = obter_numero_geracao_sequencial()
    
    # Contagem dos diferentes status de certificados
    validados_car20 = len(df[df['excepcionalidade'] == 'Validado pelo CAR 2.0'])
    nao_validado = len(df[df['excepcionalidade'] == 'Não Validado'])
    validados_status_pe = len(df[df['excepcionalidade'] == 'Validado com status Pendente'])
    
    # Quantidade total de certificados gerados
    total_certificados = len(df)
    
    # Coleta de informações do sistema
    usuario = getpass.getuser()
    data_geracao = datetime.now()
    
    # Criação do DataFrame com os metadados agregados
    dados_metadados = {
        'data_geracao': [data_geracao],
        'numero_geracao': [numero_geracao],
        'lote_geracao': [lote_geracao],
        'usuario': [usuario],
        'validados_car20': [validados_car20],
        'nao_validado': [nao_validado],
        'validados_status_pe': [validados_status_pe],
        'tipo_certificado': [tipo_certificado],
        'tentativa_suspensos': [tentativa_suspensos],
        'tentativa_cancelados': [tentativa_cancelados],
        'total_certificados': [total_certificados],  # Adicionando o total de certificados gerados
        'observacoes': ["Geração de certificados"]
    }
    
    df_metadados = pd.DataFrame(dados_metadados)
    return df_metadados

# Função obter_numero_geracao_sequencial
def obter_numero_geracao_sequencial():
    query = "SELECT MAX(numero_geracao) FROM visoes.geracoes_metadados;"
    with db.engine.connect() as conn:
        resultado = conn.execute(text(query)).fetchone()
    return resultado[0] + 1 if resultado and resultado[0] is not None else 1

# Função principal para gerar e salvar metadados
def salvar_e_gerar_metadados(df_certificados, tipo_certificado, lote_geracao, tentativa_suspensos, tentativa_cancelados, caminho_pasta):
    # Gera o DataFrame de metadados
    df_metadados = gerar_dataframe_metadados(df_certificados, tipo_certificado, lote_geracao, tentativa_suspensos, tentativa_cancelados)
    
    # Salva os metadados no banco de dados
    salvar_metadados_bd(df_metadados)
    
    # Gera o arquivo de metadados .txt
    criar_metadados(df_metadados, caminho_pasta)

    # Gerar o texto de metadados para exibição
    texto_metadados = f"""
    Data de Geração: {df_metadados['data_geracao'][0]}
    Número de Geração: {df_metadados['numero_geracao'][0]}
    Lote de Geração: {df_metadados['lote_geracao'][0]}
    Usuário: {df_metadados['usuario'][0]}
    Validados CAR 2.0: {df_metadados['validados_car20'][0]}
    Não Validados: {df_metadados['nao_validado'][0]}
    Status Pendente: {df_metadados['validados_status_pe'][0]}
    Tipo de Certificado: {df_metadados['tipo_certificado'][0]}
    Tentativa de Certificar Suspensos: {df_metadados['tentativa_suspensos'][0]}
    Tentativa de Certificar Cancelados: {df_metadados['tentativa_cancelados'][0]}
    Total de Certificados Gerados: {df_metadados['total_certificados'][0]}  # Quantidade de certificados gerados
    """
    
    return texto_metadados, lote_geracao

# Função para gerar o campo NR_SERIE com verificação e registro de erros
def gerar_nr_serie(df, caminho_lista, tipo_certificado, observacoes_metadados, lote_geracao, caminho_pasta):
    # Verificar consistência dos dados antes de gerar os números de série
    df = verificar_consistencia_dados(df)

    # Definir as colunas que não podem conter valores nulos
    colunas_obrigatorias = ['nom_municipio', 'nome_prop', 'cd_mun', 'num_area_imovel']

    # Filtrar as linhas que possuem valores nulos nessas colunas
    linhas_com_erros = df[df[colunas_obrigatorias].isnull().any(axis=1)]

    # Se houver erros, registrar os cod_imovel dessas linhas em um arquivo txt
    if not linhas_com_erros.empty:
        caminho_erros = os.path.join(caminho_pasta, 'erros_ocorridos.txt')
        with open(caminho_erros, 'w') as f:
            f.write("Lista de cod_imovel com erros:\n")
            for cod_imovel in linhas_com_erros['cod_imovel']:
                f.write(f"{cod_imovel}\n")

        # Informar quantos erros ocorreram
        print(f"Ocorreram {len(linhas_com_erros)} erros. Consulte o arquivo {caminho_erros} para mais detalhes.")

    # Remover as linhas com valores nulos para continuar o processamento
    df = df.dropna(subset=colunas_obrigatorias)

    # Se o tipo é AST, extrair nome_ast e lote_ast, senão deixar em branco
    if tipo_certificado == "ast":
        df['nome_ast'] = df['nom_imovel'].apply(extrair_nome_ast)
        df['lote_ast'] = df['nom_imovel'].apply(extrair_lote_ast)
    else:
        df['nome_ast'] = ""
        df['lote_ast'] = ""

    # Definir as variáveis cancelados e suspensos
    cancelados = df[df['ind_status_imovel'] == 'CA']
    suspensos = df[df['ind_status_imovel'] == 'SU']

    # Remover registros cancelados ou suspensos e salvar os arquivos .txt
    if not cancelados.empty:
        caminho_cancelados = os.path.join(caminho_pasta, 'cancelados.txt')
        df_cancelados = cancelados[['cod_imovel']]
        df_cancelados.to_csv(caminho_cancelados, index=False, header=False)
        df = df[~df['cod_imovel'].isin(cancelados['cod_imovel'])]

    if not suspensos.empty:
        caminho_suspensos = os.path.join(caminho_pasta, 'suspensos.txt')
        df_suspensos = suspensos[['cod_imovel']]
        df_suspensos.to_csv(caminho_suspensos, index=False, header=False)
        df = df[~df['cod_imovel'].isin(suspensos['cod_imovel'])]

    # Gerar enumeração temporária para AST
    if tipo_certificado == 'ast':
        df_enum = criar_enumeracao_lote_ast(df)
        df = df.merge(df_enum, on='cod_imovel')
    else:
        df = df.sort_values(by=['nom_municipio', 'nome_prop'])
        df['temp_enum'] = range(1, len(df) + 1)

    # Ordenar os dados conforme o tipo de certificado
    df = df.sort_values(by=['nom_municipio', 'nome_prop'] if tipo_certificado == 'iru' else ['nome_ast', 'temp_enum'])

    # Definir o formato do número de série
    dia_mes_ano_atual = datetime.now().strftime("%d%m%Y")
    # Verifique se caminho_lista é None antes de tentar usá-lo
    if caminho_lista:
        lista_certificados = pd.read_excel(caminho_lista) if os.path.exists(caminho_lista) else pd.DataFrame(columns=['nom_municipio', 'cod_imovel', 'nr_serie', 'obs', 'dt_cert', 'nome_ast', 'lote_ast'])
    else:
        lista_certificados = pd.DataFrame(columns=['nom_municipio', 'cod_imovel', 'nr_serie', 'obs', 'dt_cert', 'nome_ast', 'lote_ast'])

    # Função para contar ocorrências
    def contar_ocorrencias(cod_imovel):
        return lista_certificados[lista_certificados['cod_imovel'] == cod_imovel].shape[0]

    # Inicializar contadores e listas
    contadores = {mun: 0 for mun in df['nom_municipio'].unique()}
    serie_list = []
    obs_list = []
    dt_cert_list = []
    excepc_list = []

    # Geração dos números de série
    for index, row in df.iterrows():
        contadores[row['nom_municipio']] += 1
        nome_ast = row['nome_ast']
        codigo_numero = gerar_codigo_numero(nome_ast) if tipo_certificado == 'ast' else gerar_codigo_numero(row['nome_prop'])

        # Definir a base do número de série conforme o tipo de certificado
        if tipo_certificado == "ast":
            nr_serie_base = f"{row['cd_mun']}-{dia_mes_ano_atual}-{codigo_numero:05d}-{contadores[row['nom_municipio']]:05d}"
        else:
            nr_serie_base = f"{row['cd_mun']}-{dia_mes_ano_atual}-{contadores[row['nom_municipio']]:05d}"

        # Verificar ocorrências de múltiplos certificados para o mesmo imóvel
        ocorrencias = contar_ocorrencias(row['cod_imovel'])
        if ocorrencias > 0:
            nr_serie = f"{nr_serie_base}-{ocorrencias + 1}"
            obs = f"{ordinal(ocorrencias + 1)} ocorrência"
        else:
            nr_serie = nr_serie_base
            obs = ""

        # Preencher a coluna EXCEPCIONALIDADE
        if row['status_validacao'] == "Validado pelo CAR 2.0":
            excepc_list.append("Validado pelo CAR 2.0")
        elif row['status_validacao'] == "Não Validado":
            excepc_list.append("Não Validado")
        elif row['status_validacao'] == "Validado" and row['ind_status_imovel'] == "PE":
            excepc_list.append("Validado com status Pendente")
        else:
            excepc_list.append("")

        # Adicionar o número de série e observações às listas
        serie_list.append(nr_serie)
        obs_list.append(obs)
        dt_cert_list.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Adicionar os dados gerados ao DataFrame
    df['nr_serie'] = serie_list
    df['obs'] = obs_list
    df['dt_cert'] = dt_cert_list
    df['excepcionalidade'] = excepc_list
    df['lote'] = lote_geracao

    return df

# Função para formatar a data, substituindo por hoje se a data for nula ou NaT
def formatar_data(data):
    # Verifica se a data é nula, None ou NaT
    if pd.isnull(data) or data is None or data == pd.NaT:
        # Substitui por hoje se a data for nula ou NaT
        data = datetime.now()

    # Converte para datetime se for um objeto Timestamp do Pandas
    if isinstance(data, pd.Timestamp):
        data = data.to_pydatetime()

    # Lista de meses para formatar a data em português
    meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
    ]

    # Formata a data como 'dia de mês de ano'
    return f"{data.day} de {meses[data.month - 1]} de {data.year}"

# Função para criar uma nova pasta com numeração sequencial
def criar_pasta_data_numerada(caminho_base, lote_geracao=None):
    if lote_geracao:
        caminho_pasta = os.path.join(caminho_base, lote_geracao)
        if not os.path.exists(caminho_pasta):
            os.makedirs(caminho_pasta)
        # Verificar se o caminho_pasta não é None
        if not caminho_pasta:
            raise ValueError("Erro: caminho_pasta é None após a criação da pasta.")
        return caminho_pasta, lote_geracao
    else:
        data_atual = datetime.now().strftime("%d_%m_%Y")
        contador = 1
        while True:
            nome_pasta = f"{data_atual}_geracao_{contador}"
            caminho_pasta = os.path.join(caminho_base, nome_pasta)
            if not os.path.exists(caminho_pasta):
                os.makedirs(caminho_pasta)
                # Verificar se o caminho_pasta não é None
                if not caminho_pasta:
                    raise ValueError("Erro: caminho_pasta é None após a criação da pasta.")
                return caminho_pasta, nome_pasta
            contador += 1

# Registrar a fonte Helvetica personalizada
pdfmetrics.registerFont(TTFont('HelveticaCustom', os.path.join(os.getcwd(), 'Helvetica-Bold.ttf')))

# Função para gerar os certificados comuns (único PDF)
def gerar_certificados_comuns(df, caminho_fundo, caminho_base, tipo_certificado, observacoes_metadados, lote_geracao):
    if not lote_geracao:
        caminho_pasta, lote_geracao = criar_pasta_data_numerada(caminho_base)
    else:
        caminho_pasta = os.path.join(caminho_base, lote_geracao)
        if not os.path.exists(caminho_pasta):
            os.makedirs(caminho_pasta)

    if not os.path.exists(caminho_fundo):
        print(f"Fundo não encontrado: {caminho_fundo}")
        return
    
    erros = []

    # Caminho do arquivo PDF único
    caminho_pdf_unico = gerar_caminho_pdf(caminho_pasta, lote_geracao)
    print(f"Caminho completo do PDF gerado: {caminho_pdf_unico}")

    # Criar o canvas para o PDF único
    c = canvas.Canvas(caminho_pdf_unico, pagesize=landscape(A4))

    # Definição dos estilos de parágrafo com base no tipo de certificado
    styles = getSampleStyleSheet()
    estilo_paragrafo = ParagraphStyle(
        'Certificado',
        parent=styles['Normal'],
        fontName='HelveticaCustom',
        fontSize=14,
        leading=18,
        textColor='#1A2244' if tipo_certificado == "iru" else '#385623',
        alignment=4,  # Justificado
    )

    estilo_destaque = ParagraphStyle(
        'Destaque',
        parent=styles['Normal'],
        fontName='HelveticaCustom',
        fontSize=16,
        leading=20,
        textColor='#1A2244' if tipo_certificado == "iru" else '#385623',
        alignment=4,  # Justificado
    )

    estilo_titulo = ParagraphStyle(
        'Titulo',
        parent=styles['Normal'],
        fontName='HelveticaCustom',
        fontSize=24,
        leading=26,
        textColor='#1A2244' if tipo_certificado == "iru" else '#385623',  # Mesma cor que o restante do texto
        alignment=1,  # Centralizado
    )
    
    status_map = {
        "AT": "ATIVO",
        "PE": "PENDENTE",
        "CA": "CANCELADO",
        "SU": "SUSPENSO"
    }

    # Iterar sobre cada certificado
    for index, row in df.iterrows():
        try:
            # Configurações da página
            c.drawImage(caminho_fundo, 0, 0, width=landscape(A4)[0], height=landscape(A4)[1])
            
            largura_caixa = landscape(A4)[0] - 5 * cm  
            altura_caixa = landscape(A4)[1] - 5 * cm  
            x_margem = 2.5 * cm
            y_margem = landscape(A4)[1] - 4.5 * cm

            data_formatada = formatar_data(row['dt_validacao'] if pd.notnull(row['dt_validacao']) else datetime.now().strftime("%Y-%m-%d"))
            status_imovel = status_map.get(row['ind_status_imovel'], row['ind_status_imovel'])

            # Ajuste do texto condicional com base no tipo de certificado e status de validação
            if row['status_validacao'] == "Validado pelo CAR 2.0":
                texto_condicao = f"O CAR apresenta status ATIVO na condição Analisado sem pendências, nos termos da Lei n° 12.651, de 25 de maio de 2012 e da Instrução Normativa MMA n°2, de maio de 2014, cujas diretrizes de análise e validação foram atendidas em {data_formatada}.<br/><br/>"
            elif row['status_validacao'] == "Não Validado":
                texto_condicao = f"O CAR apresenta status ATIVO nos termos da Lei n° 12.651, de 25 de maio de 2012 e da Instrução Normativa MMA n°2, de maio de 2014, cujas diretrizes de análise e validação foram atendidas em {data_formatada}.<br/><br/>"
            else:
                texto_condicao = f"O CAR apresenta status {status_imovel} na condição {row['condicao_analise']}, nos termos da Lei n° 12.651, de 25 de maio de 2012 e da Instrução Normativa MMA n°2, de maio de 2014, cujas diretrizes de análise e validação foram atendidas em {data_formatada}.<br/><br/>"

            # Parágrafo repetitivo (Art. 4º do Decreto nº 1.148/2008)
            paragrafo_repetitivo = '<font size=10>Obs.: Art. 4º do Decreto nº 1.148/2008: O CAR-PA não autoriza qualquer atividade econômica no imóvel rural, exploração florestal, supressão de vegetação, nem se constitui em prova da posse ou propriedade para fins de regularização fundiária.</font><br/><br/>'

            # Adicionando o parágrafo repetitivo ao final do texto_condicao
            texto_condicao += paragrafo_repetitivo

            # Ajuste das quebras de linha para o tipo de certificado
            if tipo_certificado == "iru":
                quebras_linha = "<br/><br/>"
            else:
                quebras_linha = "<br/><br/><br/>"

            texto_certificado = f"""
            A Secretaria de Estado de Meio Ambiente e Sustentabilidade, por meio do Programa Regulariza Pará, confere ao imóvel a Validação do Cadastro Ambiental Rural (CAR) no Módulo de Análise do SICAR/PA.{quebras_linha}
            <font size=16></font><br/>  <!-- Espaço de 2,5 cm -->
            <font size=16>MUNICÍPIO: {row['nom_municipio'].upper()}</font><br/>
            <font size=16>IMÓVEL: {row['nom_imovel']}</font><br/>
            <font size=16>DOMÍNIO: {limpar_nome_prop(row['nome_prop'])}</font><br/>
            """
            
            # Incluir INCRA apenas para AST
            if tipo_certificado == "ast":
                texto_certificado += f"<font size=16>INCRA - SR01 CNPJ: 00.375.972/0003-22</font><br/>"
            
            texto_certificado += f"""
            <font size=16>ÁREA DO IMÓVEL: {str(row['num_area_imovel']).replace('.', ',')} ha</font><br/>
            <font size=16>N° DO RECIBO: {row['cod_imovel']}</font><br/><br/>
            {texto_condicao}
            """

            if tipo_certificado == "ast":
                titulo = row['nome_ast']
                c.setFont(estilo_titulo.fontName, estilo_titulo.fontSize)
                c.setFillColor(estilo_titulo.textColor)
                c.drawCentredString(landscape(A4)[0] / 2, landscape(A4)[1] - 7.5 * cm, titulo)

            paragrafo = Paragraph(texto_certificado.strip(), estilo_paragrafo)
            frame = Frame(x_margem, y_margem - altura_caixa, largura_caixa, altura_caixa, showBoundary=0)
            frame.addFromList([paragrafo], c)
            
            c.setFont("HelveticaCustom", 9)
            c.setFillColorRGB(1, 0, 0)
            c.saveState()
            c.translate(0.5 * cm, 0.5 * cm)
            c.rotate(90)
            c.drawString(0, -landscape(A4)[0] + 1 * cm, f"Número de Série: {row['nr_serie']}")
            c.restoreState()
            
            # Adiciona uma nova página para o próximo certificado
            c.showPage()

        except Exception as e:
            erros.append(f"{row['nr_serie']}-{row['cod_imovel']}: {e}")

    # Finalizar o PDF único
    c.save()

    # Exibir mensagem de sucesso ou erro
    if erros:
        print("Erros encontrados na geração dos seguintes arquivos:")
        for erro in erros:
            print(erro)
    else:
        print(f"Todos os certificados foram gerados com sucesso no arquivo {caminho_pdf_unico}.")

# Função para salvar lista de certificados no banco de dados
def salvar_lista_certificados_bd(df):
    try:
        # Certifique-se de que a coluna 'cod_protocolo' esteja no DataFrame
        if 'cod_protocolo' not in df.columns:
            raise ValueError("Erro: a coluna 'cod_protocolo' não foi encontrada no DataFrame.")

        # Remover a coluna 'nm_mun' se ela existir no DataFrame
        colunas_para_ignorar = ['nm_mun']
        df = df.drop(columns=[col for col in colunas_para_ignorar if col in df.columns], errors='ignore')
        current_app.logger.info(f"Colunas removidas: {colunas_para_ignorar}")

        # Limpar cache de metadados do SQLAlchemy para garantir que esteja atualizado
        db.engine.dispose()
        current_app.logger.info("Cache de metadados limpo com sucesso.")

        # Converter nomes das colunas para minúsculas
        df.columns = df.columns.str.lower()

        # Definir a tabela de destino
        tabela_destino = 'lista_certificados_gerados'
        current_app.logger.info(f"Tentando salvar dados na tabela {tabela_destino}...")

        # Inserir os dados no banco de dados usando 'to_sql'
        df.to_sql(tabela_destino, db.engine, schema='visoes', if_exists='append', index=False)
        
        # Log de sucesso
        current_app.logger.info(f"Dados salvos com sucesso na tabela {tabela_destino}.")
    
    except Exception as e:
        # Em caso de erro, reverter qualquer transação pendente e logar o erro
        db.session.rollback()
        current_app.logger.error(f"Erro ao salvar dados no banco de dados: {e}")

# Função para criar o arquivo metadados.txt
def criar_metadados(df_metadados, caminho_pasta):
    try:
        caminho_arquivo_txt = os.path.join(caminho_pasta, "metadados.txt")
        
        # Abra o arquivo e escreva os dados de forma organizada
        with open(caminho_arquivo_txt, 'w') as file:
            file.write("Metadados da Geração de Certificados\n")
            file.write("------------------------------------\n")
            for index, row in df_metadados.iterrows():
                file.write(f"Data de Geração: {row['data_geracao']}\n")
                file.write(f"Número de Geração: {row['numero_geracao']}\n")
                file.write(f"Lote de Geração: {row['lote_geracao']}\n")
                file.write(f"Usuário: {row['usuario']}\n")
                file.write(f"Validados CAR 2.0: {row['validados_car20']}\n")
                file.write(f"Não Validados: {row['nao_validado']}\n")
                file.write(f"Status Pendente: {row['validados_status_pe']}\n")
                file.write(f"Tipo de Certificado: {row['tipo_certificado']}\n")
                file.write(f"Tentativa de Certificar Suspensos: {row['tentativa_suspensos']}\n")
                file.write(f"Tentativa de Certificar Cancelados: {row['tentativa_cancelados']}\n")
                file.write(f"Total de Certificados Gerados: {row['total_certificados']}\n")  # Quantidade de certificados gerados
                file.write("------------------------------------\n")
        
        print(f"Arquivo de metadados criado com sucesso em: {caminho_arquivo_txt}")
    
    except Exception as e:
        print(f"Erro ao gerar o arquivo de metadados: {e}")

# Função para salvar metadados no banco de dados
def salvar_metadados_bd(df_metadados):
    try:
        # Certifique-se de que o DataFrame tem as colunas certas antes de salvar
        tabela_destino = 'geracoes_metadados'
        
        # Salvar no banco de dados usando pandas to_sql
        df_metadados.to_sql(tabela_destino, db.engine, schema='visoes', if_exists='append', index=False)
        
        print(f"Metadados salvos com sucesso na tabela {tabela_destino}!")
    
    except Exception as e:
        print(f"Erro ao salvar metadados no banco de dados: {e}")

# Função para criar arquivos .txt com imóveis cancelados e suspensos
def criar_arquivos_txt(cancelados, suspensos, caminho_pasta):
    # Criação dos arquivos cancelados.txt e suspensos.txt
    if not cancelados.empty:
        caminho_cancelados = os.path.join(caminho_pasta, 'cancelados.txt')
        df_cancelados = cancelados[['cod_imovel']]
        df_cancelados.to_csv(caminho_cancelados, index=False, header=False)

    if not suspensos.empty:
        caminho_suspensos = os.path.join(caminho_pasta, 'suspensos.txt')
        df_suspensos = suspensos[['cod_imovel']]
        df_suspensos.to_csv(caminho_suspensos, index=False, header=False)

# Função para gerar o caminho completo do arquivo PDF corretamente:
def gerar_caminho_pdf(caminho_pasta, lote_geracao):
    nome_pdf = f"certificados_lote_{lote_geracao}.pdf"
    return os.path.join(caminho_pasta, nome_pdf)

# ---------------------------------------------------
# Rotas Flask
# ---------------------------------------------------
from sqlalchemy import text

@app.route('/')
def index():
    try:
        # Conectando ao banco de dados e executando a consulta usando a nova API do SQLAlchemy
        with db.engine.connect() as connection:
            query = "SELECT * FROM visoes.mvw_base_dashboard_app_certificados"
            resultado = connection.execute(text(query)).mappings().fetchone()

        # Garantir que os valores sejam definidos ou que tenham um fallback para 0
        total_certificados = resultado.get('total_certificados', 0)
        total_lotes_geracao = resultado.get('total_lotes_geracao', 0)
        total_lotes_ast = resultado.get('total_lotes_ast', 0)
        total_lotes_iru = resultado.get('total_lotes_iru', 0)
        total_area_atingida = resultado.get('total_area_atingida', 0)
        total_projetos_assentamento = resultado.get('total_projetos_assentamento', 0)

        # Renderizando o template com os dados
        return render_template(
            'index.html',
            total_certificados=total_certificados,
            total_lotes_geracao=total_lotes_geracao,
            total_lotes_ast=total_lotes_ast,
            total_lotes_iru=total_lotes_iru,
            total_area_atingida=total_area_atingida,
            total_projetos_assentamento=total_projetos_assentamento
        )
    except Exception as e:
        print(f"Erro ao carregar os dados: {e}")
        return render_template('index.html', error="Erro ao carregar os dados.")
    
# Refresh na view do dashboard inicial
@app.route('/refresh', methods=['POST'])
def refresh_view():
    try:
        # Conectando ao banco de dados e atualizando a view materializada
        with db.engine.connect() as connection:
            refresh_query = "REFRESH MATERIALIZED VIEW visoes.mvw_base_dashboard_app_certificados;"
            connection.execute(text(refresh_query))
            connection.commit()  # Confirma a execução

        # Redireciona para a página inicial com uma mensagem de sucesso
        return redirect(url_for('index', message="View materializada atualizada com sucesso!"))
    except Exception as e:
        print(f"Erro ao atualizar a view materializada: {e}")
        return redirect(url_for('index', error="Erro ao atualizar a view materializada."))

@app.route('/gerar_lista')
def gerar_lista():
    return render_template('gerar_lista.html')

#Rota para sistema de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        # Tenta fazer a consulta ao banco de dados
        try:
            with db.engine.connect() as conn:
                query = text("""
                    SELECT "Usuário", "Técnico", "Senha"
                    FROM visoes.usuarios_dashboard_doc_proc 
                    WHERE "Usuário" = :usuario AND "Senha" = :senha
                """)
                # Usar o método mappings() para retornar um dicionário
                resultado = conn.execute(query, {'usuario': usuario, 'senha': senha}).mappings().fetchone()

            # Verifica se o usuário foi encontrado
            if resultado:
                session['usuario'] = resultado['Usuário']  # Agora você pode acessar por nome de campo
                session['tecnico'] = resultado['Técnico']
                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Usuário ou senha inválidos.', 'error')
                return render_template('login.html')

        except Exception as e:
            flash(f'Erro ao realizar login: {str(e)}', 'error')
            return render_template('login.html')

    return render_template('login.html')

@app.before_request
def verificar_login():
    # Permitir acesso à página de login e index sem autenticação
    rotas_livres = ['login', 'static', 'index']
    if request.endpoint not in rotas_livres and 'usuario' not in session:
        return redirect(url_for('login'))

# Renomeando a rota /index para /pagina_inicial e a função index para pagina_inicial
@app.route('/pagina_inicial')
def pagina_inicial():
    return render_template('index.html')

# Rota para fazer logout
@app.route('/logout')
def logout():
    # Limpa a sessão do usuário
    session.clear()
    flash('Você saiu com sucesso!', 'success')
    return redirect(url_for('login'))

# processar_geracao_lista
@app.route('/processar_geracao_lista', methods=['POST'])
def processar_geracao_lista():
    try:
        tipo_certificado = request.form.get('tipo_certificado')  # Obtém o tipo de certificado enviado pelo formulário
        arquivo = request.files.get('arquivo')  # Obtendo o arquivo
        
        # Verificar se o arquivo foi enviado corretamente
        if not arquivo or not arquivo.filename.endswith('.xlsx'):
            flash("Por favor, envie um arquivo Excel (.xlsx) válido.", "error")
            return redirect(url_for('gerar_lista'))

        # Ler o arquivo Excel
        df_excel = pd.read_excel(arquivo)

        # Carregar os dados já tratados da view materializada
        df_sicar = carregar_dados_postgresql()

        # Mesclar com os dados do Excel
        df_merged = pd.merge(df_excel, df_sicar, on='cod_imovel', how='left')

        # Verificar se 'cod_protocolo' está presente logo após o merge
        if 'cod_protocolo' not in df_merged.columns:
            df_merged['cod_protocolo'] = df_sicar.set_index('cod_imovel')['cod_protocolo']

        # Salvar o DataFrame em um arquivo temporário
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
        df_merged.to_pickle(temp_file.name)

        # Armazenar o caminho do arquivo e o tipo de certificado na sessão
        session['df_merged_path'] = temp_file.name
        session['tipo_certificado'] = tipo_certificado

        # Continue o processo de verificação e geração de certificados
        validado_car20, nao_validado, cancelados, suspensos, pendentes_validado = verificar_casos_adversos(df_merged)

        # Redirecionar para a página de confirmação com os totais
        return render_template('confirmar_geracao.html',
                               validado_car20=len(validado_car20),
                               nao_validado=len(nao_validado),
                               pendentes_validado=len(pendentes_validado))

    except KeyError as ke:
        flash(f"Erro ao processar a lista: {str(ke)}", "error")
        return redirect(url_for('gerar_lista'))
    except Exception as e:
        flash(f"Erro ao processar a lista: {str(e)}", "error")
        return redirect(url_for('gerar_lista'))
    
# Função para verificar e criar a coluna 'lote_invalidado' nas tabelas, caso ela não exista
def criar_coluna_lote_invalidado():
    try:
        query_verificar = """
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'geracoes_metadados' AND column_name = 'lote_invalidado';
        """
        query_criar_coluna = """
        ALTER TABLE visoes.geracoes_metadados ADD COLUMN lote_invalidado BOOLEAN DEFAULT FALSE;
        """

        with db.engine.connect() as conn:
            resultado = conn.execute(text(query_verificar)).fetchone()

            if not resultado:
                conn.execute(text(query_criar_coluna))

        print("Verificação e criação da coluna 'lote_invalidado' realizada com sucesso.")
        
    except Exception as e:
        print(f"Erro ao criar a coluna 'lote_invalidado': {e}")

# Rota para baixar planinha por lote
@app.route('/baixar_lote', methods=['GET', 'POST'])
def baixar_lote():
    if request.method == 'POST':
        numero_lote = request.form.get('lote')

        if not numero_lote:
            flash('Por favor, insira um número de lote válido.', 'error')
            return redirect(url_for('baixar_lote'))

        try:
            # Consulta SQL corrigida para usar %s com psycopg2
            query = """
            SELECT * 
            FROM visoes.lista_certificados_gerados
            WHERE lote = %s
            """
            
            # Passando o parâmetro corretamente como tupla
            df_lote = pd.read_sql_query(query, db.engine, params=(numero_lote,))

            if df_lote.empty:
                flash(f"Nenhum certificado encontrado para o lote {numero_lote}.", 'error')
                return redirect(url_for('baixar_lote'))

            # Gera o arquivo Excel em memória
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_lote.to_excel(writer, index=False, sheet_name='Certificados_Lote')

            output.seek(0)

            # Envia o arquivo XLSX para download
            return send_file(output, download_name=f'lote_{numero_lote}.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        except Exception as e:
            flash(f"Erro ao baixar o lote: {str(e)}", 'error')
            return redirect(url_for('baixar_lote'))

    return render_template('baixar_lote.html')

# Função para exibir o texto de metadados de um lote e confirmar a invalidação
def invalidar_lote(lote_geracao):
    try:
        query_metadados = """
        SELECT texto_metadados, lote_invalidado 
        FROM visoes.geracoes_metadados 
        WHERE lote_geracao = :lote_geracao;
        """
        query_invalida_lote = """
        UPDATE visoes.geracoes_metadados 
        SET lote_invalidado = TRUE 
        WHERE lote_geracao = :lote_geracao;
        """

        with db.engine.connect() as conn:
            resultado = conn.execute(text(query_metadados), {'lote_geracao': lote_geracao}).fetchone()

            if not resultado:
                print("Nenhum lote encontrado com o número fornecido.")
            else:
                texto_metadados, lote_invalidado = resultado
                if lote_invalidado:
                    print(f"O lote {lote_geracao} já está invalidado.")
                else:
                    conn.execute(text(query_invalida_lote), {'lote_geracao': lote_geracao})
                    print(f"Lote {lote_geracao} invalidado com sucesso.")
        
    except Exception as e:
        print(f"Erro ao invalidar o lote: {e}")

# Função buscar_imoveis_por_proprietario
def buscar_imoveis_por_proprietario(cpf_cnpj):
    # Usa o engine já configurado globalmente com SQLAlchemy no Flask
    query = """
        SELECT cod_imovel, nom_imovel, nom_municipio, nome_prop 
        FROM dashboard.vw_dw_sicar_v01
        WHERE cpfs_cnpjs_prop ILIKE %(cpf_cnpj)s 
        AND condicao_analise IN (
            'Analisado sem pendências', 
            'Analisado, aguardando regularização ambiental (Lei nº 12.651/2012)',
            'Analisado sem pendências CAR 2.0'
        );
    """
    
    # O '%' é um wildcard do SQL, ele é usado para buscar dentro do campo
    cpf_cnpj_pattern = f"%{cpf_cnpj}%"
    df = pd.read_sql(query, db.engine, params={"cpf_cnpj": cpf_cnpj_pattern})
    
    return df

# Rota para confirmar a seleção dos imóveis
@app.route('/confirmar_selecao', methods=['POST'])
def confirmar_selecao():
    imoveis_selecionados = request.form.getlist('imoveis_selecionados')
    tipo_certificado = request.form.get('tipo_certificado')

    if not imoveis_selecionados:
        mensagem = "Nenhum imóvel foi selecionado."
        return render_template('gerar_cpf.html', mensagem=mensagem)

    try:
        # Carregar os dados dos imóveis selecionados do SICAR
        df_imoveis = df_sicar[df_sicar['cod_imovel'].isin(imoveis_selecionados)]

        if df_imoveis.empty:
            raise ValueError("Nenhum imóvel válido encontrado na consulta.")

        # Não há mais necessidade de mesclar com df_municipios, já que cd_mun está na base
        if 'cd_mun' not in df_imoveis.columns:
            raise ValueError("Erro: a coluna 'cd_mun' não foi encontrada.")

        # Criação da pasta e geração dos certificados
        caminho_pasta, lote_geracao = criar_pasta_data_numerada(caminho_base_certificados)

        # Geração do caminho completo para o PDF único
        caminho_pdf_unico = os.path.join(caminho_pasta, f"certificados_lote_{lote_geracao}.pdf")
        print(f"Caminho completo do PDF gerado: {caminho_pdf_unico}")

        # Certifique-se de que o caminho fundo também esteja correto
        caminho_fundo = os.path.join("C:/exemplo/BASES PARA GERAÇÃO DE CERTIFICADOS/LAYOUTS", "FUNDO1.png" if tipo_certificado == 'iru' else "FUNDO2.png")
        
        df_certificados = gerar_nr_serie(df_imoveis, "", tipo_certificado, [], lote_geracao, caminho_pasta)

        # Gerar os certificados em PDF
        gerar_certificados_comuns(df_certificados, caminho_fundo, caminho_base_certificados, tipo_certificado, [], lote_geracao)

        # Chamar a função para gerar e salvar os metadados
        salvar_e_gerar_metadados(
            df_certificados, 
            tipo_certificado, 
            lote_geracao,
            len(df_certificados[df_certificados['ind_status_imovel'] == 'SU']),  # Quantidade de suspensos
            len(df_certificados[df_certificados['ind_status_imovel'] == 'CA']),  # Quantidade de cancelados
            caminho_pasta
        )

        # Gerar os metadados para exibição no template
        df_metadados = gerar_dataframe_metadados(
            df_certificados, 
            tipo_certificado, 
            lote_geracao, 
            len(df_certificados[df_certificados['ind_status_imovel'] == 'SU']), 
            len(df_certificados[df_certificados['ind_status_imovel'] == 'CA'])
        )

        # Preparar o texto dos metadados para exibição
        metadados_texto = df_metadados.to_html(index=False, classes='table table-striped')

        mensagem = f"Certificados gerados com sucesso! Lote de geração: {lote_geracao}"
        
        # Renderizar o template com o texto de metadados correto
        return render_template(
            'gerar_cpf.html', 
            mensagem=mensagem, 
            metadados_texto=metadados_texto,  # Passar os metadados como HTML
            download_link=url_for('download_file', filename=os.path.join(lote_geracao, f"certificados_lote_{lote_geracao}.pdf"))
        )

    except Exception as e:
        mensagem = f"Erro ao gerar os certificados: {str(e)}"
        return render_template('gerar_cpf.html', mensagem=mensagem)

#Rota para Download do Arquivo:
@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        # Use os.path.join para garantir que o caminho seja correto
        caminho_completo = os.path.join(caminho_base_certificados, filename)
        print(f"Path for download: {caminho_completo}")
        
        # Verifique se o arquivo existe
        if not os.path.exists(caminho_completo):
            flash(f"O arquivo {filename} não foi encontrado.")
            return redirect(url_for('gerar_cpf'))
        
        # Envie o arquivo para download
        return send_file(caminho_completo, as_attachment=True)
    except Exception as e:
        flash(f"Erro ao baixar o arquivo: {str(e)}")
        return redirect(url_for('gerar_cpf'))
    
# Rota para Download de Arquivo após gerar_lista
@app.route('/download_gerar_lista/<path:filename>')
def download_gerar_lista(filename):
    try:
        # Use os.path.join para garantir que o caminho seja correto
        caminho_completo = os.path.join(caminho_base_certificados, filename)
        print(f"Path for download: {caminho_completo}")
        
        # Verifique se o arquivo existe
        if not os.path.exists(caminho_completo):
            flash(f"O arquivo {filename} não foi encontrado.")
            return redirect(url_for('gerar_lista'))
        
        # Envie o arquivo para download
        return send_file(caminho_completo, as_attachment=True)
    except Exception as e:
        flash(f"Erro ao baixar o arquivo: {str(e)}")
        return redirect(url_for('gerar_lista'))

# Rota para a página 'gerar_cpf'
@app.route('/gerar_cpf', methods=['GET', 'POST'])
def gerar_cpf():
    if request.method == 'POST':
        cpf_cnpj = request.form.get('cpf_cnpj')
        cpf_cnpj = re.sub(r'\D', '', cpf_cnpj)  # Remove caracteres não numéricos

        try:
            # 1. Buscar imóveis por proprietário usando a função apropriada (ajustada para SQLAlchemy)
            df_imoveis = buscar_imoveis_por_proprietario(cpf_cnpj)
            
            if df_imoveis.empty:
                mensagem = "Nenhum imóvel encontrado para o CPF/CNPJ fornecido."
                return render_template('gerar_cpf.html', mensagem=mensagem)

            # 2. Se imóveis foram encontrados, renderiza a página com a lista de imóveis
            return render_template('gerar_cpf.html', df_imoveis=df_imoveis.to_dict(orient='records'))
        
        except Exception as e:
            mensagem = f"Erro ao buscar os imóveis: {str(e)}"
            return render_template('gerar_cpf.html', mensagem=mensagem)

    # Caso seja uma requisição GET, apenas renderiza a página inicial do formulário
    return render_template('gerar_cpf.html')

# Processar confirmar geração
@app.route('/confirmar_geracao', methods=['POST'])
def confirmar_geracao():
    try:
        # Recupera o caminho do arquivo do DataFrame salvo na sessão
        df_merged_path = session.get('df_merged_path')
        if not df_merged_path:
            flash("Erro ao recuperar os dados da sessão.", "error")
            return redirect(url_for('gerar_lista'))
        
        # Carregar o DataFrame a partir do arquivo
        df_merged = pd.read_pickle(df_merged_path)
        tipo_certificado = session.get('tipo_certificado')

        # Coletar as escolhas do usuário
        gerar_car20 = request.form.get('gerar_car20')
        gerar_nao_validados = request.form.get('gerar_nao_validados')
        gerar_pendentes = request.form.get('gerar_pendentes')

        # Verificar os casos adversos
        validado_car20, nao_validado, cancelados, suspensos, pendentes_validado = verificar_casos_adversos(df_merged)

        # Aplicar as escolhas do usuário
        if gerar_car20 != "Sim" and not validado_car20.empty:
            df_merged = df_merged[~df_merged['cod_imovel'].isin(validado_car20['cod_imovel'])]

        if gerar_nao_validados != "Sim" and not nao_validado.empty:
            df_merged = df_merged[~df_merged['cod_imovel'].isin(nao_validado['cod_imovel'])]

        if gerar_pendentes != "Sim" and not pendentes_validado.empty:
            df_merged = df_merged[~df_merged['cod_imovel'].isin(pendentes_validado['cod_imovel'])]

        # Continuar o processo de geração de certificados
        caminho_pasta, lote_geracao = criar_pasta_data_numerada(caminho_base_certificados)
        df_certificados = gerar_nr_serie(df_merged, None, tipo_certificado, [], lote_geracao, caminho_pasta)

        caminho_fundo = os.path.join(
            "C:/exemplo/BASES PARA GERAÇÃO DE CERTIFICADOS/LAYOUTS",
            "FUNDO1.png" if tipo_certificado == 'iru' else "FUNDO2.png"
        ).replace("\\", "/")

        gerar_certificados_comuns(df_certificados, caminho_fundo, caminho_pasta, tipo_certificado, [], lote_geracao)
        
        # Chamar a função para gerar e salvar os metadados, agora retornando o texto gerado
        texto_metadados, lote_geracao = salvar_e_gerar_metadados(
            df_certificados, 
            tipo_certificado, 
            lote_geracao,
            len(df_certificados[df_certificados['ind_status_imovel'] == 'SU']),  # Quantidade de suspensos
            len(df_certificados[df_certificados['ind_status_imovel'] == 'CA']),  # Quantidade de cancelados
            caminho_pasta
        )

        # Salvar os certificados no banco de dados
        salvar_lista_certificados_bd(df_certificados)

        # Redirecionar para a página com o texto de metadados e o link de download
        return render_template(
            'gerar_lista.html',
            mensagem=f"Certificados gerados com sucesso!\n{texto_metadados}",
            download_link=url_for('download_file', filename=os.path.join(lote_geracao, lote_geracao, f"certificados_lote_{lote_geracao}.pdf"))
        )

    except Exception as e:
        flash(f"Erro ao gerar os certificados: {str(e)}")
        return redirect(url_for('gerar_lista'))

# Rota para a página 'gerar_arquivos_modelo'
@app.route('/gerar_arquivos_modelo')
def gerar_arquivos_modelo():
    caminho_modelo = criar_arquivo_modelo()
    return send_file(caminho_modelo, as_attachment=True)

# Rota para a página 'anular_lote'
@app.route('/anular_lote')
def anular_lote():
    return render_template('anular_lote.html')

@app.route('/processar_anulacao_lote', methods=['POST'])
def processar_anulacao_lote():
    lote_geracao = request.form.get('lote')
    
    if not lote_geracao:
        flash('Por favor, insira um número de lote válido.', 'error')
        return redirect(url_for('anular_lote'))

    try:
        # Verificar se o lote existe e seu status de invalidação
        query_metadados = """
        SELECT lote_invalidado 
        FROM visoes.geracoes_metadados 
        WHERE lote_geracao = :lote_geracao;
        """

        query_invalida_lote = """
        UPDATE visoes.geracoes_metadados 
        SET lote_invalidado = TRUE 
        WHERE lote_geracao = :lote_geracao;
        """

        with db.engine.connect() as conn:
            # Executar a consulta de verificação
            resultado = conn.execute(text(query_metadados), {'lote_geracao': lote_geracao}).fetchone()

            if not resultado:
                flash(f"Nenhum lote encontrado com o número {lote_geracao}.", 'error')
                return redirect(url_for('anular_lote'))
            
            # Verificar se o lote já está invalidado
            if resultado[0]:
                flash(f"O lote {lote_geracao} já está invalidado.", 'error')
                return redirect(url_for('anular_lote'))

            # Realizar o UPDATE para invalidar o lote
            resultado_update = conn.execute(text(query_invalida_lote), {'lote_geracao': lote_geracao})
            
            # Verificar se o update foi bem-sucedido
            if resultado_update.rowcount == 0:
                flash(f"Erro: Nenhum lote foi atualizado para o número {lote_geracao}.", 'error')
            else:
                flash(f"Lote {lote_geracao} invalidado com sucesso!", 'success')

            # Garantir o commit, caso o banco de dados não faça autocommit
            conn.commit()

    except Exception as e:
        print(f"Erro ao invalidar o lote: {e}")
        flash(f"Erro ao invalidar o lote: {str(e)}", 'error')

    # Redirecionar de volta para a página de anulação
    return redirect(url_for('anular_lote'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)