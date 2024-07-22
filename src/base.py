from datetime import date
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

    def show_previous_workout(self, phase, split, day):
        self._previous_workout = None
        previous_workout = self.previous_workout
        try:
            previous_workout = previous_workout[(previous_workout['Phase'] == phase) & (previous_workout['Split'] == split) & (previous_workout['Day'] == day)]
            last_workout_date = previous_workout['Date'].max()
            previous_workout = previous_workout[previous_workout['Date'] == last_workout_date]
            previous_workout.drop(columns=['Date','Phase', 'Split', 'Day'], inplace=True)
        except KeyError:
            st.warning('Previous workout not found')
            previous_workout = pd.DataFrame()
        return previous_workout

    @staticmethod
    def try_parse_number(value, func):
        try:
            func(value)
            return True
        except (ValueError, TypeError):
            return False

    def get_workout_plan(self, phase, split, day):
        df = self.conn.read(worksheet='Workouts')
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

    def save_workout(self, edited_workout, phase, split, day):
        workout = edited_workout
        previous_workout = self.previous_workout

        today = date.today().strftime('%Y-%m-%d')

        workout.insert(0, 'Date', today)
        workout.insert(1, 'Phase', phase)
        workout.insert(2, 'Split', split)
        workout.insert(3, 'Day', day)
        workout = workout.dropna(subset=['Exercise'])

        reps_cols = [col for col in workout.columns if 'reps' in col]
        weight_cols = [col for col in workout.columns if 'weight' in col]

        reps = workout[reps_cols].values.flatten().tolist()
        weight = workout[weight_cols].values.flatten().tolist()

        print(reps[2], type(reps[2]), str(reps[2]) == 'nan')
        print(weight[2], type(weight[2]), str(weight[2]) == 'nan')

        reps = [int(x) if x is not None and self.try_parse_number(x, int) else None if str(x) == 'nan' else x for x in reps]
        weight = [int(x) if self.try_parse_number(x, int) and '.' not in x else None if str(x) == 'nan' else float(x) if self.try_parse_number(x, float) else x for x in weight]

        print(reps)
        print(weight)

        reps_split = [reps[i:i + self.max_sets] for i in range(0, len(reps), self.max_sets)]
        weight_split = [weight[i:i + self.max_sets] for i in range(0, len(weight), self.max_sets)]

        print(reps_split)
        print(weight_split)

        workout['Weights'] = pd.Series(weight_split)
        workout['Reps'] = pd.Series(reps_split)

        workout = workout.drop(columns=reps_cols + weight_cols)

        if not previous_workout.empty:
            workout = pd.concat([previous_workout, workout], ignore_index=True)
            workout = workout.drop_duplicates(subset=['Date', 'Phase', 'Split', 'Day', 'Exercise'], keep='last')

        self.conn.update(worksheet=self.person, data=workout)