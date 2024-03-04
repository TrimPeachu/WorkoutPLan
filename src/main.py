import logging
import numpy as np
import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)


class WorkoutPlan:
    def __init__(self):
        self.exercise_list = None
        self.workout_plan = None
        self.max_sets = None
        self._exercises = None
        self._previous_workout = None

    @property
    def previous_workout(self):
        if self._previous_workout is None:
            try:
                df = pd.read_csv(r'data/previous_workouts.csv')
                self._previous_workout = df
            except FileNotFoundError:
                logger.info('No previous workouts found')
                self._previous_workout = pd.DataFrame()
        return self._previous_workout

    def show_previous_workout(self, person, split, day):
        previous_workout = self.previous_workout
        previous_workout.drop(['person', 'week', 'split', 'day'], axis=1).dropna(how='all', axis=1)
        previous_workout = previous_workout[(previous_workout['person'] == person) & (previous_workout['split'] == split) & (previous_workout['day'] == day)]
        return previous_workout

    @staticmethod
    def get_phase(week):
        if week <= 6:
            return 1
        elif 6 < week <= 10:
            return 2
        elif 10 < week <= 13:
            return 3

    def get_workout_plan(self, week, split, day):
        df = pd.read_csv(r'data/workoutplan.csv')
        phase = self.get_phase(week)
        df = df[(df['week'] == phase) & (df['split'] == split) & (df['day'] == day)]
        self.workout_plan = df[['exercise', 'warm_up', 'sets', 'reps', 'rpe', 'alternative_1', 'alternative_2']]
        self.max_sets = max(self.workout_plan['sets'])

        return self.workout_plan

    @property
    def exercises(self):
        if self._exercises is None:
            df = self.workout_plan
            exercises = df['exercise'].unique()
            alternatives_1 = df['alternative_1'].dropna().unique()
            alternatives_2 = df['alternative_2'].dropna().unique()

            exercise_list = list(set(np.concatenate([exercises, alternatives_1, alternatives_2])))
            exercise_list.sort()
            self._exercises = exercise_list

        return self._exercises

    def draw_workout_plan(self):
        workout_dict = {}
        for i in range(0, len(self.workout_plan)):
            workout_dict[i] = {'exercise': None}
        for i in range(0, self.max_sets + 1):
            for j in range(1, len(self.workout_plan)):
                workout_dict[j][f'weight_{i}'] = None
                workout_dict[j][f'reps_{i}'] = None

        workout_df = pd.DataFrame(workout_dict).T
        print(workout_df)
        print(self.workout_plan)
        workout_df['exercise'] = self.workout_plan['exercise']
        print(workout_df)
        edited_workout = st.data_editor(workout_df,
                                        hide_index=True,
                                        column_config={
                                            "exercise": st.column_config.SelectboxColumn(
                                                "Exercise",
                                                options=self.exercises,
                                                required=True,
                                                width="medium"
                                            )
                                        })

        return edited_workout

    def save_workout(self, edited_workout, person, week, split, day):
        workout = edited_workout
        previous_workout = self.previous_workout

        workout.insert(0, 'person', person)
        workout.insert(1, 'week', week)
        workout.insert(2, 'split', split)
        workout.insert(3, 'day', day)
        workout = workout.dropna(subset=['exercise'])

        if not previous_workout.empty:
            workout = pd.concat([previous_workout, workout], ignore_index=True)
            workout = workout.drop_duplicates(subset=['person', 'week', 'split', 'day', 'exercise'], keep='last')
        workout.to_csv(r'data/previous_workouts.csv', index=False)


def main():
    st.set_page_config(page_title="Workout Plan")
    st.title('Workout Plan')

    workout_planner = WorkoutPlan()

    person = st.radio('Select person', ['Tomas', 'Sebko'])
    week = st.number_input('Enter week number', format='%d', value=1, min_value=1, max_value=20, step=1)
    split = st.radio('Select split', ['Push', 'Pull', 'Legs'])
    day = st.radio('Variation', [1, 2])

    st.write('## Workout Plan')
    show_plan = workout_planner.get_workout_plan(week, split, day)
    st.dataframe(show_plan, hide_index=True)

    st.write('## Previous Workout')
    st.dataframe(workout_planner.show_previous_workout(person, split, day), hide_index=True)

    st.write('## Track your workout')
    edited_workout = workout_planner.draw_workout_plan()

    if st.button('Save workout'):
        workout_planner.save_workout(edited_workout, person, week, split, day)


if __name__ == '__main__':
    main()
