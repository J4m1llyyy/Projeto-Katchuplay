from flask import Flask, render_template, request, redirect, url_for
import json
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# Configuração dos caminhos dos arquivos JSON
FILMES_FILE = "database/filmes.json"
GENEROS_FILE = "database/generos.json"

# Função para ler os dados dos arquivos JSON
def carregar_json(arquivo):
    if not os.path.exists(arquivo):
        return []
    with open(arquivo, "r", encoding="utf-8") as f:
        return json.load(f)

# Função para gravar os dados nos arquivos JSON
def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# Carrega os dados na memória ao iniciar o servidor
filmes = carregar_json(FILMES_FILE)
generos = sorted(carregar_json(GENEROS_FILE)) # Já ordena ao carregar

# Garante que a lista de gêneros tenha um conteúdo inicial se estiver vazia
if not generos:
    generos = ["Ação", "Comédia", "Drama", "Ficção Científica", "Terror"]
    salvar_json(GENEROS_FILE, generos)

# Rota da Home: lista os filmes
@app.route('/')
def p_inicial():
    filmes_atualizados = carregar_json(FILMES_FILE)
    return render_template('p_inicial.html', filmes=filmes_atualizados)

# Rota de listagem com filtros de busca
@app.route("/filmes", methods=["GET"])
def filmes_page():
    lista_completa = carregar_json(FILMES_FILE)
    genero = request.args.get("genero")
    classificacao_indicativa = request.args.get("classificacao_indicativa")
    return render_template(
        "p_filmes.html",
        generos=sorted(generos), # Envia gêneros ordenados para o HTML
        genero_selecionado=genero,  
        classificacao_indicativa=classificacao_indicativa,
        filmes=lista_completa  
    )

# Validador de Classificação: garante que apenas formatos permitidos sejam salvos
def processar_classificacao(valor):
    permitidos = ["L", "10+", "12+", "14+", "16+", "18+"]
    return valor if valor in permitidos else "L"

# Validador de Ano: garante que seja um ano real entre 1888 e hoje
def validar_ano(ano):
    ano_str = str(ano).strip()
    ano_atual = datetime.now().year
    if len(ano_str) == 4 and ano_str.isdigit():
        ano_int = int(ano_str)
        if 1888 <= ano_int <= ano_atual:
            return ano_str
    return str(ano_atual)

# Formatador de Duração: transforma "130" em "2h10m"
def formatar_duracao(valor):
    if not valor or not str(valor).isdigit():
        return "0h00m"
    total = int(valor)
    horas = total // 100
    mins = total % 100
    if mins >= 60:
        horas += mins // 60
        mins = mins % 60
    return f"{horas}h{mins:02d}m"

@app.route("/excluir/<string:titulo>")
def excluir_filme(titulo):
    global filmes
    lista_de_filmes = carregar_json(FILMES_FILE)
    nova_lista = [f for f in lista_de_filmes if f["titulo"] != titulo]
    salvar_json(FILMES_FILE, nova_lista)
    filmes = nova_lista
    return redirect(url_for("filmes_page"))






# Rota para Criar filme (suporta Prévia e Salvar)
@app.route("/criar", methods=["GET", "POST"])
def criar():
    lista_generos_ordenada = sorted(carregar_json(GENEROS_FILE))
    
    if request.method == "GET":
        return render_template("criar.html", generos=lista_generos_ordenada, filme=None)

    # Processamento dos campos do formulário
    titulo = request.form.get("titulo")
    genero = request.form.get("genero")
    duracao_input = request.form.get("duracao")
    classificacao_formatada = processar_classificacao(request.form.get("classificacao_indicativa"))
    ano_validado = validar_ano(request.form.get("ano"))
    duracao_formatada = formatar_duracao(duracao_input)
    
    # Upload da imagem
    imagem = request.files.get("imagem")
    filename = "default.jpg"
    if imagem and imagem.filename != '':
        filename = secure_filename(imagem.filename)
        imagem.save(os.path.join("static/images", filename))
    
    caminho_imagem = "/static/images/" + filename
    
    novo_filme = {
        "titulo": titulo,
        "ano": ano_validado,
        "genero": genero,
        "classificacao_indicativa": classificacao_formatada,
        "duracao": duracao_formatada,
        "imagem": caminho_imagem
    }

    # Lógica do botão de prévia
    if request.form.get("acao") == "previa":
        return render_template("criar.html", generos=lista_generos_ordenada, filme=novo_filme)

    # Salva definitivamente
    filmes.append(novo_filme)
    salvar_json(FILMES_FILE, filmes)
    return redirect(url_for("p_inicial"))







@app.route("/editarFilmes/<string:titulo>", methods=["GET", "POST"])
def editar(titulo):
    global filmes
    lista_de_filmes = carregar_json(FILMES_FILE)
    filme = next((f for f in lista_de_filmes if f["titulo"] == titulo), None)
    lista_generos_ordenada = sorted(carregar_json(GENEROS_FILE))
    
    if not filme:
        return redirect(url_for("filmes_page"))

    if request.method == "POST":
        # 1. Atualiza dados básicos
        filme["titulo"] = request.form.get("titulo")
        filme["genero"] = request.form.get("genero")
        filme["ano"] = validar_ano(request.form.get("ano"))
        filme["classificacao_indicativa"] = processar_classificacao(request.form.get("classificacao_indicativa"))
        filme["duracao"] = formatar_duracao(request.form.get("duracao"))

        # 2. Lógica de Imagem
        acao = request.form.get("acao")
        
        # Lógica de Remoção
        if acao == "remover":
            filme["imagem"] = "none"
            salvar_json(FILMES_FILE, lista_de_filmes) 
            filmes = lista_de_filmes 
            return render_template("editar.html", filme=filme, generos=lista_generos_ordenada)
        
        # Lógica de Upload (Sempre processa se houver arquivo, independente do botão clicado)   
        if 'imagem' in request.files:
            imagem = request.files['imagem']
            if imagem and imagem.filename != '':
                # Usar timestamp evita conflito de nomes e garante que o navegador busque a imagem nova
                filename = f"{int(datetime.now().timestamp())}_{secure_filename(imagem.filename)}"
                caminho_salvar = os.path.join("static/images", filename)
                imagem.save(caminho_salvar)
                filme["imagem"] = f"/static/images/{filename}"

        # 3. SALVAMENTO DEFINITIVO
        salvar_json(FILMES_FILE, lista_de_filmes)
        filmes = lista_de_filmes 
        return redirect(url_for("filmes_page"))

    return render_template("editar.html", filme=filme, generos=lista_generos_ordenada)

if __name__ == "__main__":
    app.run(debug=True)