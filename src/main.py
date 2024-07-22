import logging
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

from homepage import homepage

logger = logging.getLogger(__name__)


def main():

    homepage()

    #TODO: Implement multi-page navigation
    # pg = st.navigation([
    #     st.Page(homepage, title="Workout Tracker"),
    #     st.Page(data_page, title="Data")
    # ])
    #
    # pg.run()


if __name__ == '__main__':
    main()
