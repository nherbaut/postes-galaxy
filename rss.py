# coding: utf-8
import os

from flask import Flask, request, make_response
app = Flask(__name__)
import re
from lxml import etree
import feedgenerator
import requests
import os
import logging

@app.route("/html.xsl")
def get_xsl():
  with open("/var/www/rss/rss2html.xsl") as f:
    return make_response(f.read(),200)

@app.route('/', defaults={'search': ""})
@app.route('/<search>')
def get_data(search):
  subdomain,aformat,domain,tld=request.headers['Host'].split(".")
  if aformat=="rss":
    return query_rss(search,subdomain,html=False)
  if aformat=="html":
    return query_rss(search,subdomain,html=True)
  else:
    return make_response(render_template('you are here for the rss right?'), 404)
    
def xsl_transform(xml):
  xslt = etree.parse("/var/www/rss/rss2html.xsl")
  transform = etree.XSLT(xslt)
  newdom = transform(etree.XML(xml))
  return "<!-- " + xml + " !-->" + etree.tostring(newdom, pretty_print=True)

def query_rss(search,subdomain,html):
  match=re.findall("((?:mcf)|(?:pr))((?:[0-9]{0,2}-?)*)",subdomain)
  if len(match)==0:
    return make_response(render_template('invalid request, please specify the corps and the cnu number such as: mcf27 or pr5'), 404)
  grade, section_url = match[0]
  if len(search)>0:
    searchexp = search.encode('utf8')
  else:
    searchexp = ".*"

  ptcorps=grade
  ptsection="pour la (les)  section(s) %s " % (" ou ".join(section_url.split("-")) if len(section_url)>0 else "")
  if request.headers['Host'].split(".")[1]=="2017":
    source={"2017" : "https://nextnet.top/sites/default/files/ListePostePubliesAnnuelle2017.xls" }
  else:
    source={"Publie".encode("utf8"):"https://www.galaxie.enseignementsup-recherche.gouv.fr/ensup/ListesPostesPublies/Emplois_publies_TrieParCorps.html", "Prepublie".encode("utf8"):"https://www.galaxie.enseignementsup-recherche.gouv.fr/ensup/ListesPostesPublies/Emplois_prepublies_TrieParCorps.html"}

  total_onwebsite=0
  matching=0
  feed=[]
  for k,v in source.items():
    response = requests.get(v)
    doc = response.text
    # the data from galaxie is in latin1
    doc = doc.encode("utf8")
    tree = etree.HTML(doc)
    postes = tree.xpath('//table/tr/td/table/tr')
    total_onwebsite+=len(postes)
    for i in postes:
      ids = i.xpath('td[position()=3]/a/text()') # called re galaxie
      idposte = 'inconnu' if len(ids) == 0 else ids[0]
      links = i.xpath('td[position()=3]/a/@href')
      link = 'inconnu' if len(links) == 0 else links[0]
      # skip first line, that seems to be always empty
      if link == "inconnu":
        continue
      domaines = i.xpath('td[position()=14]/text()')
      domaine = 'inconnu' if len(domaines) == 0 else domaines[0]
      #print domaine
      institutions = i.xpath('td[position()=2]/text()')
      institution = 'inconnu' if len(institutions) == 0 else institutions[0]
      #print institution
      # PR or MCF?
      types_poste = i.xpath('td[position()=6]/text()')
      type_poste = 'inconnu' if len(types_poste) == 0 else types_poste[0]
      if type_poste.lower() != grade.lower():
        continue
      # PR or MCF?
      sections=[]
      for sec_col in range(8,11):
        sec = i.xpath('td[position()=%d]/text()'%sec_col)
        if len(sec)>0:
          sections.append(sec[0])
      if len(set(sections) & set(section_url.split("-")))==0  and len(section_url)>0:
        continue
      description = "Profil : "+domaine+"; Institution : "+institution+"; Section : "+" ou ".join(sections)+ "; Ref poste : "+idposte
      if re.match(".*("+searchexp+").*", description, flags = re.IGNORECASE | re.MULTILINE | re.DOTALL | re.UNICODE):
        matching+=1
        feed.append(("[ " + k + " ] " + type_poste+" "+domaine+" - "+institution,  link,       description,       link))
  rssfeed = feedgenerator.Rss201rev2Feed(title="Poste de %s %s" % (grade,ptsection) ,
       description="Liste des %d/%d postes d'enseignant-chercheur prépubliés, publiés et ouverts à  la candidature" % ( matching,total_onwebsite),
       link="https://www.galaxie.enseignementsup-recherche.gouv.fr/ensup/ListesPostesPublies/Emplois_publies_TrieParCorps.html",
       language="fr")
  
  for item in feed:
    rssfeed.add_item(title=item[0],link=item[1],description=item[2],unique_id=item[3])
  rss_content=rssfeed.writeString('utf-8')
  if html:
    resp = make_response(xsl_transform(rss_content),200)
    resp.headers["Content-type"]="text/html"
  else:
    resp = make_response(rss_content,200)
    resp.headers["Content-type"]="application/rss+xml"
  resp.headers["charset"]="utf8"
  return resp

