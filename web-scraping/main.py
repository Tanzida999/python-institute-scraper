import requests
from bs4 import BeautifulSoup
url ="https://www.codewithharry.com/"

#get the html file
r = requests.get(url)
htmlContent = r.content 
# print(htmlContent)

#parse the html
soup = BeautifulSoup(htmlContent, 'html.parser')
# print(soup.prettify())
# get the title of the html page
title =soup.title
print(type(title))
#get all the paragraphs from the page
# print(soup.find_all('p'))
#get all anchor from the page
# print(soup.find_all('a'))
print(soup.find('p')['class'])
#printing the parsed data in a pretty way
