import pandas as pd
import numpy as np
import re
import sklearn
import streamlit as st
import requests
import pickle

#Prikupljanje podataka 
Filmovi= pickle.load(open("data/movies.pkl","rb"))
le_tconst = pickle.load(open('data/label_encoder_tconst.pkl', 'rb')) 
Genres = pickle.load(open("data/genres.pkl","rb"))
zanr_opcije = np.sort(list(set(Genres.columns) - set(['genres_label','Genres'])))


#Postavljanje izgleda stranice same aplikacije
st.set_page_config(layout="wide", page_title="Sistem preporuke filmova")
API_KEY = '3c810a39'
show_columns = ['Title','Rating','Votes','Genres', 'Year','Runtime']

#upute za koristenje
st.sidebar.title("Pronađite svoj sljedeći omiljeni film!")
st.sidebar.write("Ovaj sistem dozvoljava korisniku da odabere žanr, "
                "godinu snimanja i slične parametre filma kako bi mu "
                "potom dao na odabir grupu filmova koji najbolje odgovaraju"
                "željenim parametrima. Prvi film koji se pojavi je najbolji odabir."
                "Sve recenzije, kritike i podatci su uzeti s IMDB-a, "
                "Rotten Tomatoes i Metacritica.")



#odabir zeljenih parametara
godine_filmovi= st.slider('Odaberi godinu snimanja', 1899, 2021, (1995, 2021))
recenzije_filmovi= st.slider('Odaberi IMDB recenziju', 1,10,(6,10))
glasovi_filmovi= st.slider('Odaberi broj recenzija na IMDB-u', 20,2500000, (100000,1000000))
vrijeme_trajanja_filmovi= st.slider('Odaberi vrijeme trajanja filma', 2,1500,(90,240))

#stavranje varijable koja filtrira podatke po zadanim parametrima
Film_subset = Filmovi[(Filmovi.Year        >= godine_filmovi[0])    & \
                    (Filmovi.Year        <= godine_filmovi[1])    & \
                    (Filmovi.Rating      >= recenzije_filmovi[0])  & \
                    (Filmovi.Rating      <= recenzije_filmovi[1])  & \
                    (Filmovi.Votes       >= glasovi_filmovi[0])   &\
                    (Filmovi.Votes       <= glasovi_filmovi[1])   &\
                    (Filmovi.Runtime     >= vrijeme_trajanja_filmovi[0]) &\
                    (Filmovi.Runtime     <= vrijeme_trajanja_filmovi[1])]

odabir_zanra= st.multiselect('Odaberi jedan ili više žanrova', zanr_opcije, ['crime','drama'])
labels_odabir_zanra = Genres.loc[\
    Genres[odabir_zanra].sum(axis = 1) == len(odabir_zanra),'genres_label']

#filtriranje po zanru
Film_subset = Film_subset[Film_subset.genres_label.isin(labels_odabir_zanra)]

#krajnji dataset sortiran po ocjeni i nazivu filma
Film_subset = Film_subset.sort_values(by = ['Rating','Title'], ascending = False).reset_index()

 

########################### DETALJI FILMOVA #################################
st.markdown("""---""")
st.subheader("Detalji filmova")

#IMDB ID
movie_select    = st.selectbox(f'Odaberi bilo koji od {Film_subset.shape[0]} filmova iz odabrane grupe za detalje', Film_subset.Title)
movie_select_id = Film_subset.loc[Film_subset.Title==str(movie_select),'tconst'].item()
movie_imdb_id   = le_tconst.inverse_transform([movie_select_id]).item() # pretvara integer u orginalnu IMDB ID vrijednost

#Orginalno ime
movie_name_formatted = re.sub('[^0-9a-zA-Z]+', ' ',str(movie_select)).replace(" ", "_").lower()
if movie_name_formatted[len(movie_name_formatted )-1] == "_":
    movie_name_formatted = movie_name_formatted[:-1]

#Korisni linkovi
url_imdb = "https://www.imdb.com/title/"         + str(movie_imdb_id) + '/'
url_rt   = "https://www.rottentomatoes.com/m/"   + movie_name_formatted
url_yt   = "https://www.youtube.com/results?search_query="   + movie_name_formatted.replace("_", "-") + '+trailer'
url_letterboxd  = "https://letterboxd.com/film/" + movie_name_formatted.replace("_", "-")

#Poseban slučaj ukoliko stranica ne da konkretan film, izbacit ce se rezultat pretrazivanja 
if requests.get(url_rt).status_code != 200: 
    url_rt = 'https://www.rottentomatoes.com/search?search=' + movie_name_formatted.replace("_", "%20")
if requests.get(url_letterboxd).status_code != 200: 
    url_letterboxd = 'https://letterboxd.com/search/' + movie_name_formatted.replace("_", "")

st.write("Pogledajte " + str(movie_select) + " na [IMDB](%s)" % url_imdb + ", [Rotten Tomatoes](%s)" % url_rt + \
    ", [Letterboxd](%s)" % url_letterboxd +' direktno ili pogledajte najavu na [YouTube](%s)' % url_yt + ' ovdje.')

#Prikupljanje informacija pomocu API ključa
def get_OMDB(movieID, API_KEY):
    OMDB_info      = requests.get('http://www.omdbapi.com/?i='+ movieID + '&apikey=' + API_KEY).json()
    withoutRatings = pd.json_normalize(data = OMDB_info).set_index('imdbID')
    withoutRatings = withoutRatings.loc[:,withoutRatings.columns!='Ratings']
    Ratings        = pd.json_normalize(data=OMDB_info, record_path='Ratings').set_index('Source').T
    Ratings.index  = withoutRatings.index
    movie_complete = Ratings.merge(withoutRatings, right_index = True, left_index = True)
    relevant_cols  = ['Internet Movie Database','Rotten Tomatoes','Metacritic','BoxOffice','Plot','Actors','Awards','Writer','Poster']
    for relevant_col in relevant_cols:
        try:
            movie_complete[relevant_col] = movie_complete[relevant_col]
        except:
            movie_complete[relevant_col] = 'N/A'
    return movie_complete

#prikaz ocjene sa date stranice
OMDB_query = get_OMDB(movie_imdb_id, API_KEY)
col1, col2, col3, col4 = st.columns(4)
col1.metric("IMDB",            OMDB_query['Internet Movie Database'].item())
col2.metric("Rotten Tomatoes", OMDB_query['Rotten Tomatoes'].item())
col3.metric("Metacritic",      OMDB_query['Metacritic'].item())
col4.metric("Box Office",      OMDB_query['BoxOffice'].item())

scol1, scol2 = st.columns((1, 4))   
# plot
scol2.subheader("Sadržaj filma")
scol2.write(OMDB_query['Plot'].item())
# main actors
scol2.subheader('Uloge')
scol2.write(OMDB_query['Actors'].item())
# awards
scol2.subheader('Nagrade')
scol2.write(OMDB_query['Awards'].item())
# director(s)
scol2.subheader('Redatelji')
scol2.write(OMDB_query['Director'].item())
# writer(s)
scol2.subheader('Pisac')
scol2.write(OMDB_query['Writer'].item())
scol1.image(OMDB_query['Poster'].item())
#############################################################################



######################### POPIS PREPORUČENIH FILMOVA ########################
st.markdown("""---""")
st.subheader(f'{Film_subset.shape[0]} preporučenih filmova koji odgovaraju zadanim kriterijima')
show_columns_Film_subset = show_columns
suffix_table_expander = 'koji odgovaraju zadanim kriterijima' 

see_selected_Filmovi = st.expander('👉Klikni ovdje da pogledaš preporuke ' + suffix_table_expander)
with see_selected_Filmovi:
    st.dataframe(Film_subset[show_columns_Film_subset].style.format({'Year': '{:.0f}', 'Rating': '{:.1f}',\
            'Runtime': '{:.0f}','Votes': '{:.0f}'}),height=500, width = 5500)
#############################################################################



######################## SLIČNI FILMOVI #####################################
st.markdown("""---""")
st.subheader('Filmovi slični ' + str(movie_select))
similar_tconsts_to_selected = Filmovi[Filmovi.tconst == movie_select_id].similar_tconsts.item()
if ~np.isnan(similar_tconsts_to_selected).any():
    df_similar = Filmovi[Filmovi.tconst.isin(similar_tconsts_to_selected)].sort_values(by = ['Rating','Title'], ascending = False).reset_index()
    see_similar_Filmovi = st.expander('👉 Klikni ovdje da pogledaš filmove koji su slični odabarnom filmu ' + str(movie_select))
    with see_similar_Filmovi:
        st.dataframe(df_similar[show_columns].style.format({'Year': '{:.0f}', 'Rating': '{:.1f}',\
            'Runtime': '{:.0f}','Votes': '{:.0f}'}),height=500, width = 5500)
else:
    st.write('Niti jedan film sličan ' + str(movie_select) + ' nije pronađen')   

##############################################################################
