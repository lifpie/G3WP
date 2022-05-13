from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import date
from bs4 import BeautifulSoup
import requests
import re
import json

# * Apontamento do diretorio onde está o driver do Chrome (versão 101 dos navegadores).
# * Logo mais é iniciado o Webdriver utilizando o driver especificado.
PATH = "C:\Program Files (x86)\chromedriver.exe"
driver = webdriver.Chrome(PATH)
today = date.today() # * Data de hoje.

# * Site para coleta de dados
driver.get("https://nvd.nist.gov/vuln/search")

#TODO: Na integração substituir as variaveis por valores de input
data_busca = "03052022" #! A entrada de data deve estar no padrão americano mm dd YY
sw_sch = "microsoft" 

#TODO: Adicionar verificador do status do site para evitar crashs (com a biblioteca requests)
try:
    #* Função para buscar a localização do botão  que muda para modo "Advanced"
    #* Foi utilizado funções da biblioteca Selenium Webdriver para localizar o botão.
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "SearchTypeAdvanced"))
    )    
    element.click() #* Método que clica automaticamente no local especificado na variavel "element".

    #####
    #* Localizando o campo de data inicial da busca.
    #TODO: Insirir limitador para periodos de até 120 dias.
    inp_date = driver.find_element(By.ID,"published-start-date")   
    inp_date.send_keys(data_busca)  #* Método que insere a data no campo especificado.

    #####
    inp_date = driver.find_element(By.ID, "published-end-date")
    aday = today.strftime("%m%d%Y") #* Utilizando a biblioteca "datetime" para inserir a data atual do PC.
    inp_date.send_keys(aday)
    
    #####
    #* Inserindo o software a ser pesquisado. 
    inp_sw = driver.find_element(By.ID, "Keywords")
    inp_sw.send_keys(sw_sch)

    #####
    #* Apertando o botão de "Search".
    #? Seria bom tratar erros na busca? (Ex.: Periodo maior que 120 dias)
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "vuln-search-submit"))
    )
    element.click()

    #####
    #TODO: Verificar se a linha abaixo é necessaria.
    url_n = driver.current_url

    #####
    #! A partir desse momento será utilizando muito mais o BeautifulSoup para tratar a HTML e o requests para acessar elas.
    #* Usando o Requests para baixar a HTML e o Soup para "tratar" ela.
    response = requests.get(url_n)
    content_t = response.content
    site_t = BeautifulSoup(content_t, 'html.parser')

    #####
    #* O for foi utilizado para localizar todos os <a> da HTML e a frente serão selecionados aqueles que possuem o termo "CVE"
    for link in site_t.find_all('a'):
        refadv = []
        severity = []
        affec =[]
        src_lst = []
        cpe_cd = []
        publi_d = ''
        if 'CVE' in str(link.contents):
            #* Os links contidos na variavel localizada estavam incompletos, sendo necessario concatenar as str e gerar novo link.
            new_link = "https://nvd.nist.gov" + str(link.get('href'))

            driver.get(new_link)
            cont_new = requests.get(new_link)
            cont_new_t = cont_new.content
            site_n_t = BeautifulSoup(cont_new_t, 'html.parser')
            #print(site_n_t.prettify())

            #####
            #* Utilizando método find do BS para localizar o código CVE, armazenado na variavel cve_cd.
            cve_cd = site_n_t.find(attrs = {'data-testid':'page-header-vuln-id'})
            cve_cd = str(cve_cd.contents)[1:-1] #* Retirado caracteres a mais.

            #####
            #* Mesmo modelo utilizado anterior mente agora para loclaizar a descrição.
            descrit = site_n_t.find('p', attrs={'data-testid': 'vuln-description'})
            descrit = str(descrit.contents)[1:-1]

            #####
            #* Utilizando o método "find_all" do BS para localizar os graus de severidade anotados da vunerabilidade.
            for busca in site_n_t.find_all(attrs={'id': re.compile('Cvss3')}):
                severity.append(str(busca.contents)[2:-2]) #? Verificar se é possivel identificar cada uma das notas
            
            #####
            #* Mesmo principio porem agora para localizar links de esclarecimento do fornecedor do software
            #* OBS.: Foi utilizado a biblioteca re junto com métodos compile para localizar de maneria geral palavras
            #* que contenham a parte já especificada (inserido palavra parcial)
            for busca in site_n_t.find_all(attrs= {'data-testid' : re.compile("vuln-hyperlinks-link-")}):
                refadv.append(busca.text)
            
            #####
            #* Iniciando com try pois existem casos em que não é especificado o código "CPE" e quando ocorria o sw bugava.
            try:
                #####
                #* Localizado a linha do HTML com json(s) inserido(s).
                for busca in site_n_t.find_all('input', attrs= {'id' : re.compile("cveTreeJsonDataHidden")}):
                    tens = busca
                
                #####
                #* Retirado o(s) json da linha do HTML e feito o split para casos em que há mais de um json.
                js_part = tens['value'][1:-1].split("[]}]}]},")

                #####
                #* Elaborado lista com os json corrigidos após o split.
                for ptr in range(0,len(js_part)):
                    if ptr == len(js_part)-1:
                        src_lst.append(js_part[ptr])
                    else:
                        src_lst.append(js_part[ptr]+"[]}]}]}")
                
                #####
                #* Utilizado a biblioteca json + método loads para converter ele em um dicionario e ser tratado no codigo.
                for rg in range(0,len(src_lst)):
                    scr = json.loads(src_lst[rg])
                    cpe_cd.append(scr["containers"][0]["containers"][0]["cpes"][0]["cpe23Uri"]) #? Seria possivel melhorar?
                    #? Esse levantamento foi feito com base no padrão da loclaização da informação, mas está muito "truncado"                    
            except:
                cpe_cd.append("None")

            #####
            #* Mesma logica já utilizado para localizar conteudo com palavras parciais, agora para localizar a data de publicação.
            for busca in site_n_t.find_all(attrs= {'data-testid' : re.compile("vuln-published-on")}):
                publi_d = str(busca.contents)

            print("Código CVE: ", cve_cd)
            print("Descrição: ", descrit)
            print("Severidade: ", severity)
            print("Referencia: ", refadv)
            print("Código CPE: ", cpe_cd)
            print("Data de publicação: ", publi_d)
            print("Site da CVE", new_link)
            #time.sleep(1)
            driver.back()
    #####
    #TODO: Pendente trabalhar na mudança de pagina da tabela com todos os CVE.
    time.sleep(5)
except:
    driver.quit()
