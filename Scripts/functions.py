# Functions

!pip install -U sentence-transformers
!pip install happytransformer
!pip3 install qwikidata
from qwikidata.sparql import return_sparql_query_results
from IPython.core.debugger import skip_doctest
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel, AutoModelForTokenClassification
from transformers import pipeline
from happytransformer import HappyTextToText, TTSettings
from sklearn.metrics.pairwise import cosine_similarity
import re
import json
import time
import torch
import torch.nn.functional as F
import nltk
from nltk.corpus import wordnet
nltk.download('wordnet')
nltk.download('omw-1.4')


# Execute a SPARQL query that retrieves the superclasses of an entity in Wikidata
def runSPARQLQuery(id):
  sparql_query = f"""
        SELECT DISTINCT ?cLabel WHERE {{
          wd:{id} wdt:P31/wdt:P279? ?c .
          ?c rdfs:label ?cLabel .
          FILTER(LANG(?cLabel) = "en")      
        }}
        """
  res = return_sparql_query_results(sparql_query)
  return res

# Retrieve the JSON result from the SPARQL query
def getSPARQLResult(result):
  results = list()
  valueList = result['results']['bindings']
  for j in valueList:
    value = j['cLabel']['value']
    results.append(value)
  return results

# Get noun synsets when provided a value
def getSynsets(value):
  synsetList = list()
  synsets = wordnet.synsets(value, pos='n')
  for i in synsets:
    synsetList.append(i)
  return(synsetList)

# Get synset definition when provided with a synset
def getSynsetDefinition(synset):
  synsetDefinition = synset.definition()
  return(synsetDefinition)


# Mean Pooling - Take attention mask into account for correct averaging (For sentence embedding)
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

# Sentence embedding
def sentenceEmbedding(sentence):
  # Sentences we want sentence embeddings for
  sentences = [sentence]
  # Load model from HuggingFace Hub
  tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
  model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
  # Tokenize sentences
  encoded_input = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')
  # Compute token embeddings
  with torch.no_grad():
    model_output = model(**encoded_input)
  # Perform pooling
  sentence_embedding = mean_pooling(model_output, encoded_input['attention_mask'])
  # Normalize embeddings
  sentence_embedding = F.normalize(sentence_embedding, p=2, dim=1)
  # Return embeddings
  return sentence_embedding

# Sentence similarity
def sentenceSimilarity(feature_vec_1, feature_vec_2):
  return cosine_similarity(feature_vec_1.reshape(1, -1), feature_vec_2.reshape(1, -1))[0][0]

# Named entity recognition
def sentenceNER(sentence):
  # Load model from HuggingFace Hub
  tokenizer = AutoTokenizer.from_pretrained("Jean-Baptiste/camembert-ner")
  model = AutoModelForTokenClassification.from_pretrained("Jean-Baptiste/camembert-ner")
  # Provide parameters
  nlp = pipeline('ner', model=model, tokenizer=tokenizer, aggregation_strategy="simple")
  NER = nlp(sentence)
  return NER

# Grammar check
def sentenceGrammarCheck(sentence):
  # Load model from HuggingFace Hub
  happy_tt = HappyTextToText("T5", "vennify/t5-base-grammar-correction")
  args = TTSettings(num_beams=5, min_length=1)
  # Perform task
  result = happy_tt.generate_text(sentence, args=args)
  return result.text 

# String replacer
def generalize(sentence, pattern : dict):
  for key in pattern.keys():
    if len(key) > 3 and pattern[key] != "Wikidata instance class" and pattern[key] != "Class" and pattern[key] != "":
      sentence = re.sub("(?i)"+key, pattern[key], sentence)
      sentence = sentence.capitalize()
  return sentence

# Remove special characters
def detectSpecialCharacters(mystring):
  special_characters = '.'  
  #special_characters = '"!@#$%^&*()+_=,.<>/"'
  if any(c in special_characters for c in mystring):
    return True
  else:
    return False

