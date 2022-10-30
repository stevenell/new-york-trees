import pandas as pd
import numpy as np
from dash import html, dcc, Dash
from dash.dependencies import Input, Output
import plotly.express as px

url = ('https://data.cityofnewyork.us/resource/nwxe-4ae8.json?' +\
        '$select=spc_common,boroname,health,steward,count(tree_id)' +\
        '&$group=spc_common,boroname,health,steward' +\
        '&$limit=50000'
           ).replace(' ', '%20')
data = pd.read_json(url)
data.columns = ['species','borough','health','steward','count']

#there are just a few rows with NAs, it doesn't seem worth trying to impute or anything like that
data = data.loc[data.species.isna()==False,:]
data = data.loc[data.health.isna()==False,:]


#Get key dictionaries for each value

species_list = sorted(data.species.unique(),key=lambda s: s.strip('\'"').lower())
species = dict()
for i,spec in enumerate(species_list):
    species[i]=spec

health = {0:'Poor', 1:'Fair', 2:'Good'}
steward = {0:'None', 1:'1or2', 2:'3or4', 3:'4orMore'}
borough = {0:'Bronx', 1:'Brooklyn', 2:'Manhattan', 3:'Queens', 4:'Staten Island'}


data.health = data.health.map({v: k for k, v in health.items()}).astype('int')
data.steward = data.steward.map({v: k for k, v in steward.items()}).astype('int')
data.borough = data.borough.map({v: k for k, v in borough.items()}).astype('int')
data.species = data.species.map({v: k for k, v in species.items()}).astype('int')

# going to give the stewards better labels. Assuming they mean MORE THAN 4 instead of 4 or more
steward = {0:'None', 1:'1 or 2', 2:'3 or 4', 3:'More than 4'}

#app = JupyterDash(__name__)
app = Dash(__name__)
server = app.server

tab1 = html.Div([
    html.H1("Health by Borough"),
    html.Label('Select Bureau'),

    dcc.Dropdown(
        id='borough-dropdown', clearable=True,
        value=None, options=[
            {'label': v, 'value': k}
            for k,v in borough.items()
        ]
    ),

    html.Label('Sort By'),
    dcc.Dropdown(
        id='sort-dropdown', clearable=False,
        value='Count', options=[
            {'label': 'Alpha', 'value': 'Alpha'},
            {'label': 'Total Count of Species in Borough', 'value': 'Count'},
            {'label': 'Average Health of Species Population','value': 'Health'}
        ]),

    html.Label('Use Proportion within Species or Full Count?'),
    dcc.Dropdown(
        id='prop-dropdown', clearable=False,
        value='Proportion', options=[
            {'label': 'Proportion', 'value': 'Proportion'},
            {'label': 'Full Counts', 'value': 'Full Counts'}
        ]),
    html.Label('Filter dataset by minimum number of Trees'),
    dcc.Slider(min=0, max=100, step=25,
           value=0,
           id='count-filter'
    ),
    dcc.Graph(id = 'graph-output-1')
])

tab2 = html.Div([
    html.H1("Value of Stewards"),
    html.Label('Select Bureau'),
    
    dcc.Dropdown(
        id='borough-dropdown', clearable=True,
        value=None, options=[
            {'label': v, 'value': k}
            for k,v in borough.items()
        ]
    ),

    html.Label('Select Species'),
    
    dcc.Dropdown(
        id='species-dropdown', clearable=True,
        value=None, options=[
            {'label': v, 'value': k}
            for k,v in species.items()
        ]
    ),

    dcc.Graph(id = 'graph-output-2')
])    

app.layout = html.Div([
    dcc.Tabs(id="tabs-example", value='tab-1', children=[
        dcc.Tab(id="tab-1", label='Health of Trees by Borough', value='tab-1'),
        dcc.Tab(id="tab-2", label='Stewardship of Species', value='tab-2'),
    ]),
    html.Div(id='tabs-content-example',
             children = tab1)
])

@app.callback(Output('tabs-content-example', 'children'),
             [Input('tabs-example', 'value')])
def render_content(tab):
    print(tab)
    if tab == 'tab-1':
        return tab1
    elif tab == 'tab-2':
        return tab2


@app.callback(
    Output('graph-output-1', 'figure'),
    [
    Input('borough-dropdown', 'value'),
    Input('sort-dropdown', 'value'),
    Input('prop-dropdown', 'value'),
    Input('count-filter', 'value')
         ]
)


def tab_1_graph(b,s,p,c):
    print(b,s,p,c)
    
    if b is None:
        df = data[['species','health','count']].groupby(['species','health']).sum().reset_index()
    else:
        df = data.loc[data.borough==b,['species','health','count']].groupby(['species','health']).sum().reset_index()
    
    #Get full counts for hover text:
    temp_df = df[['species','count']].groupby('species').sum().reset_index()
    sort_map = {int(x['species']):x['count'] for i,x in temp_df.iterrows()}
    df['Full Count'] = df['species'].map(sort_map)
    
    
    #Filter by count
    temp_df = df[['species','count']].groupby('species').sum().reset_index()
    df= df.loc[df['species'].isin(list(temp_df.loc[temp_df['count']>=c,'species'])),:]

    
    #sort
    if s=='Alpha':
        spec_sort = [v for k,v in species.items()]
    elif s=='Health':
        temp_df = df.groupby('species').apply(lambda x: np.average(x.health, weights=x['count'])).reset_index()
        temp_df.columns = ['species','avg_health']
        #sort_map = {int(x['species']):x['avg_health'] for i,x in temp_df.iterrows()}
        #df['sort_value'] = df['species'].map(sort_map)
        spec_sort = temp_df.sort_values('avg_health',ascending=True).species.unique()
        spec_sort = [species[x] for x in spec_sort]
    else:

        spec_sort = df.sort_values('Full Count',ascending=True).species.unique()    
        spec_sort = [species[x] for x in spec_sort]

    # Totals or Proportions
    if p =='Proportion':
        temp_df = df[['species','count']].groupby('species').sum().reset_index()
        prop_map = {int(x['species']):x['count'] for i,x in temp_df.iterrows()}
        df['count'] = df.apply(lambda x:  x['count']/prop_map[x['species']], axis=1)
        count_label = 'Proportion of Trees'
    else:
        count_label = 'Count of Trees'
        
    temp_df=None
    
    df['species'] = df.species.map(species)

    df.sort_values('health',inplace=True,ascending=False)
    df.health=df.health.map(health)
    
    df = df.rename(columns={'count': count_label, 'species': "Species",'health': 'Health Rating'})

    
    fig = px.bar(df, y="Species"
                 , x=count_label
                 , color="Health Rating"
                 , barmode="stack"
                 , color_discrete_map={'Good': 'rgb(58,183,129)', 'Fair': 'rgb(200,170,60)', 'Poor': 'rgb(120,40,40)'}
                 ,hover_name='Species'
                 ,hover_data={count_label:':.2f',
                              'Health Rating':False,
                              'Full Count':True,
                              'Species':False, 
                             }
                )


    fig.update_layout(yaxis={"dtick":1,'categoryorder':'array','categoryarray':spec_sort}
                      ,margin={"t":0,"b":0}
                      ,height=3000
                      )
    return fig

@app.callback(
    Output('graph-output-2', 'figure'),
    [
    Input('borough-dropdown', 'value'),
    Input('species-dropdown', 'value')
         ]
)


def tab_2_graph(b,s):
    print(b,s)
    if b is not None:
        if s is not None:
            df = data.loc[(data.borough==b) & (data.species==s),['steward','health','count']].groupby(['steward','health']).sum().reset_index()
        else:
            df = data.loc[(data.borough==b),['steward','health','count']].groupby(['steward','health']).sum().reset_index()
    else:
        if s is not None:
            df = data.loc[(data.species==s),['steward','health','count']].groupby(['steward','health']).sum().reset_index()
        else:
            df = data[['steward','health','count']].groupby(['steward','health']).sum().reset_index()
        
    
    spec_sort = [v for k,v in steward.items()]
    
    #Get full counts for hover text:
    temp_df = df[['steward','count']].groupby('steward').sum().reset_index()
    sort_map = {int(x['steward']):x['count'] for i,x in temp_df.iterrows()}
    df['Full Count'] = df['steward'].map(sort_map)
    
    
    

    temp_df = df[['steward','count']].groupby('steward').sum().reset_index()
    prop_map = {int(x['steward']):x['count'] for i,x in temp_df.iterrows()}
    df['count'] = df.apply(lambda x:  x['count']/prop_map[x['steward']], axis=1)
    df['steward'] = df.steward.map(steward)
    count_label = 'Proportion of Trees'

    temp_df=None
    
    df.sort_values('health',inplace=True,ascending=False)
    df.health=df.health.map(health)
    
            
    df = df.rename(columns={'count': count_label, 'steward': "Number of Stewards",'health': 'Health Rating'})

    
    fig = px.bar(df, y="Number of Stewards"
                 , x=count_label
                 , color="Health Rating"
                 , barmode="stack"
                 , color_discrete_map={'Good': 'rgb(58,183,129)', 'Fair': 'rgb(200,170,60)', 'Poor': 'rgb(120,40,40)'}
                 ,hover_name='Number of Stewards'
                 ,hover_data={count_label:':.2f',
                              'Health Rating':False,
                              'Full Count':True,
                              'Number of Stewards':False, 
                             }
                )


    fig.update_layout(yaxis={"dtick":1,'categoryorder':'array','categoryarray':spec_sort}
                      ,margin={"t":0,"b":0}
                      ,height=200
                      )
    return fig
#app.run_server(mode='inline')

if __name__ == '__main__':
    app.run_server(debug=True)
    
    
  
