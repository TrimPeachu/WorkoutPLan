import logging
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

logger = logging.getLogger(__name__)


class WorkoutPlan:
    def __init__(self):
        self.exercise_list = None
        self.workout_plan = None
        self.max_sets = 0
        self._exercises = None
        self._previous_workout = None
        self._conn = None
        self.person = None

    @property
    def conn(self):
        if self._conn is None:
            conn = st.connection('gsheets', type=GSheetsConnection)
            self._conn = conn
        return self._conn

    @property
    def previous_workout(self):
        if self._previous_workout is None:
            df = self.conn.read(worksheet=self.person, ttl=3600)
            self._previous_workout = df
        return self._previous_workout

    def show_previous_workout(self, split, day):
        self._previous_workout = None
        previous_workout = self.previous_workout
        try:
            previous_workout.dropna(how='all', axis=1, inplace=True)
            previous_workout = previous_workout[(previous_workout['Split'] == split) & (previous_workout['Day'] == day)]
        except KeyError:
            st.warning('Previous workout not found')
            previous_workout = pd.DataFrame()
        return previous_workout

    @staticmethod
    def try_parse_int(value):
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def get_phase(week):
        if week <= 6:
            return 1
        elif 6 < week <= 10:
            return 2
        elif 10 < week <= 13:
            return 3

    def get_workout_plan(self, week, split, day):
        df = self.conn.read(worksheet='Workouts')
        phase = self.get_phase(week)
        df = df[(df['Phase'] == phase) & (df['Split'] == split) & (df['Day'] == day)]
        self.workout_plan = df[['Exercise', 'Warm_up', 'Sets', 'Reps', 'RPE', 'alternative_1', 'alternative_2']]
        if self.workout_plan.empty:
            st.error('Workout plan not found')
        else:
            max_sets = max(self.workout_plan['Sets'])
            self.max_sets = int(max_sets)

        return self.workout_plan

    @property
    def exercises(self):
        if self._exercises is None:
            df = self.workout_plan
            exercises = df['Exercise'].unique()
            alternatives_1 = df['alternative_1'].dropna().unique()
            alternatives_2 = df['alternative_2'].dropna().unique()

            exercise_list = list(set(np.concatenate([exercises, alternatives_1, alternatives_2])))
            exercise_list.sort()
            self._exercises = exercise_list

        return self._exercises

    def draw_workout_plan(self):
        workout_dict = {}
        for i in range(0, len(self.workout_plan)):
            workout_dict[i] = {'Exercise': None}
        for i in range(0, self.max_sets):
            for j in range(1, len(self.workout_plan)):
                workout_dict[j][f'weight_{i+1}'] = None
                workout_dict[j][f'reps_{i+1}'] = None

        workout_df = pd.DataFrame(workout_dict).T
        workout_df['Exercise'] = self.workout_plan['Exercise'].values
        edited_workout = st.data_editor(workout_df,
                                        hide_index=True,
                                        column_config={
                                            "Exercise": st.column_config.SelectboxColumn(
                                                "Exercise",
                                                options=self.exercises,
                                                required=True,
                                                width="medium"
                                            )
                                        })

        return edited_workout

    def save_workout(self, edited_workout, week, split, day):
        workout = edited_workout
        previous_workout = self.previous_workout

        workout.insert(0, 'Week', week)
        workout.insert(1, 'Split', split)
        workout.insert(2, 'Day', day)
        workout = workout.dropna(subset=['Exercise'])

        reps_cols = [col for col in workout.columns if 'reps' in col]
        weight_cols = [col for col in workout.columns if 'weight' in col]

        reps = workout[reps_cols].values.flatten().tolist()
        weight = workout[weight_cols].values.flatten().tolist()

        reps = [int(x) if x is not None and self.try_parse_int(x) else x for x in reps]
        weight = [int(x) if x is not None and self.try_parse_int(x) else x for x in weight]

        reps_split = [reps[i:i + self.max_sets] for i in range(0, len(reps), self.max_sets)]
        weight_split = [weight[i:i + self.max_sets] for i in range(0, len(weight), self.max_sets)]

        workout['Weights'] = pd.Series(weight_split)
        workout['Reps'] = pd.Series(reps_split)

        workout = workout.drop(columns=reps_cols + weight_cols)

        if not previous_workout.empty:
            workout = pd.concat([previous_workout, workout], ignore_index=True)
            workout = workout.drop_duplicates(subset=['Week', 'Split', 'Day', 'Exercise'], keep='last')

        self.conn.update(worksheet=self.person, data=workout)


def main():
    st.set_page_config(page_title="Workout Tracker", page_icon="💪")
    st.title('Workout Tracker')

    workout_planner = WorkoutPlan()

    workout_planner.person = st.radio('Select person', ['Tomas', 'Sebko'])
    week = st.number_input('Enter week number', format='%d', value=1, min_value=1, max_value=20, step=1)
    split = st.radio('Select split', ['Push', 'Pull', 'Legs'])
    day = st.radio('Variation', [1, 2])

    st.write('## Workout Plan')
    show_plan = workout_planner.get_workout_plan(week, split, day)
    if not show_plan.empty:
        st.dataframe(show_plan, hide_index=True)

    st.write('## Previous Workout')
    previous_workout = workout_planner.show_previous_workout(split, day)
    if not previous_workout.empty:
        st.dataframe(previous_workout, hide_index=True)

    st.write('## Track your workout')
    edited_workout = workout_planner.draw_workout_plan()

    left, _, right = st.columns(3)
    if left.button('Save workout'):
        workout_planner.save_workout(edited_workout, week, split, day)

    if right.button('Reload'):
        st.rerun()


if __name__ == '__main__':
    main()
