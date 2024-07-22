from base import WorkoutPlan

import streamlit as st


def homepage():
    st.set_page_config(page_title="Workout Tracker", page_icon="💪")
    st.title('Workout Tracker')

    workout_planner = WorkoutPlan()

    workout_planner.person = st.radio('Select person', ['Tomas', 'Sebko'])
    phase = st.radio('Select phase', [1, 2, 3])
    split = st.radio('Select split', ['Push', 'Pull', 'Legs'])
    day = st.radio('Variation', [1, 2])

    st.write('## Workout Plan')
    show_plan = workout_planner.get_workout_plan(phase, split, day)
    if not show_plan.empty:
        st.dataframe(show_plan, hide_index=True)

    st.write('## Previous Workout')
    previous_workout = workout_planner.show_previous_workout(phase, split, day)
    if not previous_workout.empty:
        st.dataframe(previous_workout, hide_index=True)

    st.write('## Track your workout')
    edited_workout = workout_planner.draw_workout_plan()

    left, _, right = st.columns(3)
    if left.button('Save workout'):
        workout_planner.save_workout(edited_workout, phase, split, day)

    if right.button('Reload'):
        st.rerun()