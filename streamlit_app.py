import streamlit as st
import pandas as pd
import pydash
import plotly.express as px
import plotly.graph_objects as go
import re

st.set_page_config(layout="wide")

EVENT_TYPES = [
    "CommitCommentEvent",
    "CreateEvent",
    "DeleteEvent",
    "ForkEvent",
    "GollumEvent",
    "IssueCommentEvent",
    "IssuesEvent",
    "PullRequestEvent",
    "PullRequestReviewCommentEvent",
    "PullRequestReviewEvent",
    "PushEvent",
    "ReleaseEvent",
    "WatchEvent",
    "MemberEvent",
    "PublicEvent",
]
DEFAULT_EVENT_SET = sorted(
    [
        "ForkEvent",
        "PullRequestEvent",
        "IssuesEvent",
        "PushEvent",
        "WatchEvent",
    ]
)
DEFAULT_PROJECTS = ["Ethereum"]
METADATA_PATH = "./data/2022-10-18-project_df.csv"
CONTRIBS_DATA_PATH = "./data/2022-10-18-contributor_stats_by_month.csv"
EVENTS_DATA_PATH = "./data/2022-10-18-gharchive_event_counts_by_month.csv"

def create_search_pat(selected_projects):
    pat = rf'{"|".join([rf"^{p}$" for p in selected_projects])}'
    return pat


def create_line_plot(df, title="", **options):
    fig = (
        px.scatter(df, x="date", y="contributor_count", color="title", **options)
        .update_traces(mode="lines")
        .update_layout(xaxis=dict(title=""), yaxis=dict(title=""), title=title, legend=dict(title=""))
        .update_xaxes(rangeslider_visible=False)
    )
    return fig
def create_area_plot(df, title="", **options):
    fig = (
        px.area(df, x="date", y="contributor_count", color="title", **options)
        .update_traces(mode="lines")
        .update_layout(xaxis=dict(title=""), yaxis=dict(title=""), title=title, legend=dict(title=""))
        .update_xaxes(rangeslider_visible=False)
    )
    for i in range(len(fig['data'])):
        fig['data'][i]['line']['width']=0
    return fig

def create_faceted_bar_chart(df, filter_vals, filter_key="title", x="date", y="event_count", color="type", facet_row="title", title='', **kwargs):
    filter_pat = f"{filter_key}.isin(@filter_vals)"
    print(filter_pat)
    subset = df.query(filter_pat).sort_values('date')
    fig = px.bar(subset, x=x, y=y,color=color,facet_row=facet_row, barmode="group", **kwargs).update_layout(legend=dict(title=""))
    fig = fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    
    # hide subplot y-axis titles and x-axis titles
    for axis in fig.layout:
        if type(fig.layout[axis]) == go.layout.YAxis:
            fig.layout[axis].title.text = ''
        if type(fig.layout[axis]) == go.layout.XAxis:
            fig.layout[axis].title.text = ''
            
    return fig.update_layout(title=title)


def convert_type(col, type_):
    def f(df):
        return df[col].astype(type_)

    return f


def convert_date(col):
    def f(df):
        return pd.to_datetime(df[col])

    return f


@st.cache
def load_contribs_df(path=CONTRIBS_DATA_PATH):
    dtypes = {"date": convert_date("date")}
    df = pd.read_csv(path).assign(date=convert_date("date"))

    return df


def create_tag_set(df, col, as_list=True):
    return (
        pydash.chain(df[col].values.tolist())
        .map(lambda tags: tags.split(",") if isinstance(tags, str) else "None")
        .flatten()
        .map(lambda s: s.strip())
        .filter(lambda s: s != "")
        .thru(set)
        .thru(lambda s: sorted(list(s)) if as_list else s)
        .value()
    )


@st.cache
def load_metadata(path):

    df = pd.read_csv(
        path,
        usecols=["title", "tags"],
    )
    df["tags"] = df.tags.where(~df.tags.isna(), "None")
    projects = sorted(df.title.values.tolist())
    tags = [t.upper() for t in create_tag_set(df, "tags", as_list=True)]
    return df, projects, tags


def filter_df_by_tags(df, tags):
    tag_pat = rf"{'|'.join(tags)}"

    mask = df.tags.str.contains(tag_pat, flags=re.I, regex=True)
    return df[mask].title.values.tolist()


def create_agg_plot(df, val_col="contributor_count", title=''):
    df = df.groupby("date")[val_col].sum().reset_index()
    fig = (
        px.scatter(df, x="date", y=val_col, title="")
        .update_traces(mode="lines")
        .update_layout(
            title=title,
            xaxis=dict(title=""),yaxis=dict(title=""),
            legend_title="",
        )
        .update_xaxes(rangeslider_visible=False)
    )
    return fig

@st.cache
def load_events_df(path=EVENTS_DATA_PATH, event_types=DEFAULT_EVENT_SET):
    df = pd.read_csv(path)
    df = df[df["type"].isin(event_types)]
    return df
meta_df, projects, tags = load_metadata(METADATA_PATH)
contribs_df = load_contribs_df()
events_df = load_events_df()

st.title("Crypto Developer Tracker")
st.header("Introduction")
st.header("Methodology")
st.markdown("""
#### Electric Capital
Primary source of projects and their respective github organizations and repos was Electric Capital's open source [Crypto Ecosystem repo](https://github.com/electric-capital/crypto-ecosystems).   

> *Crypto Ecosystems is a taxonomy for sharing data around open source blockchain, Web3, cryptocurrency, and decentralized ecosystems and tying them to GitHub organizations and code repositories.   
> All of the ecosystems are specified in TOML configuration files.*

#### Github Events Archive
Open source dataset of all events triggered by public Github repos.  
See [Github Event docs](https://docs.github.com/en/developers/webhooks-and-events/events/github-event-types) for further details on event types.
#### Github API
Endpoints used:
- (Repo metadata)[https://docs.github.com/en/rest/repos] - forks, created_at, etc.
- (Repo stats)[https://docs.github.com/en/rest/metrics/statistics] - contributor activity 
#### Tagging and Metadata
Consolidated categories and labels from various data sources including Messari, DefiLlama, Coingecko.  

#### Further work
- Include commits / contributors from all branches
- Clean, consolidate, and add more tags to enable more accurate cross-sectional analyses
- Further interactive analysis of interesting developer trends across / within ecosystems
""")
st.header("Select projects")
selected_projects = st.multiselect("Projects", projects, ["Ethereum"], label_visibility="hidden")
project_pat = create_search_pat(selected_projects)

plot_df = contribs_df[
    contribs_df.title.str.contains(project_pat, flags=re.I, regex=True)
]
plot_options = {"log_y": False}
contribs_fig = create_line_plot(plot_df, title="Monthly Developer Count", **plot_options)

events_fig = create_faceted_bar_chart(events_df, selected_projects, title="Monthly GitHub Event Counts", log_y=False)

st.plotly_chart(contribs_fig, use_container_width=True)
st.plotly_chart(events_fig, use_container_width=True)

st.header("Select tags")
selected_tags = st.multiselect("Tags", tags, tags[7], label_visibility="hidden")
tagged_project_set = filter_df_by_tags(meta_df, selected_tags)
tagged_plot_df = contribs_df[contribs_df.title.isin(tagged_project_set)]
tagged_fig = create_area_plot(
    tagged_plot_df,
    title=f"Monthly Developer Count by Protocols tagged {' or '.join(t for t in selected_tags)}", log_y=False
)
agg_fig = create_agg_plot(tagged_plot_df, title=f"Total Monthly Developer Count across all protocols tagged {' or '.join(selected_tags)}")

st.plotly_chart(agg_fig, use_container_width=True)
st.plotly_chart(tagged_fig, use_container_width=True)

# st.header("Select Events")
# events = sorted(EVENT_TYPES)
# selected_events = st.multiselect("Events", events, DEFAULT_EVENT_SET)
# st.write(f"Events: {selected_events}")
