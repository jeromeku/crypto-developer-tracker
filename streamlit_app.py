import streamlit as st
import pandas as pd
import pydash
import plotly.express as px
import re

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


def create_search_pat(selected_projects):
    pat = rf'{"|".join([rf"^{p}$" for p in selected_projects])}'
    return pat


def create_line_plot(df, title="", **options):
    fig = (
        px.scatter(df, x="date", y="contributor_count", color="title", **options)
        .update_traces(mode="lines")
        .update_layout(xaxis=dict(title=""), title=title, legend=dict(title=""))
        .update_xaxes(rangeslider_visible=True)
    )
    return fig


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
            xaxis=dict(title=""),
            legend_title="",
        )
        .update_xaxes(rangeslider_visible=True)
    )
    return fig

st.title("Crypto Developer Tracker")
meta_df, projects, tags = load_metadata(METADATA_PATH)

st.header("Select projects")
selected_projects = st.multiselect("Projects", projects, ["Ethereum"])

project_pat = create_search_pat(selected_projects)

contribs_df = load_contribs_df()

plot_df = contribs_df[
    contribs_df.title.str.contains(project_pat, flags=re.I, regex=True)
]

plot_options = {"log_y": False}
fig = create_line_plot(plot_df, **plot_options)
st.plotly_chart(fig)

st.header("Select tags")
selected_tags = st.multiselect("Tags", tags, tags[:2])
tagged_project_set = filter_df_by_tags(meta_df, selected_tags)
tagged_plot_df = contribs_df[contribs_df.title.isin(tagged_project_set)]
tagged_fig = create_line_plot(
    tagged_plot_df,
    title=f"Developer Count by Protocols tagged {' or '.join(t for t in selected_tags)}",
)
agg_fig = create_agg_plot(tagged_plot_df, title=f"Total Developer Count across all protocols tagged {', '.join(selected_tags)}")

st.plotly_chart(agg_fig)
st.plotly_chart(tagged_fig)

st.markdown("Charts across projects Events and Contributors")
st.header("Select Events")
events = sorted(EVENT_TYPES)
selected_events = st.multiselect("Events", events, DEFAULT_EVENT_SET)
st.write(f"Events: {selected_events}")
