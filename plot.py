
from __future__ import annotations

import datetime
import math
import pathlib
import re
import shutil
from copy import copy
from copy import deepcopy

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch
from ruamel.yaml import YAML
from tabulate import tabulate

from analysis.utils import paths
from analysis.utils.mplstyles import PAPER

plt.style.use(PAPER)

# Possible names appended to the end of container images.
SNAPSHOTTER_IMAGE_NAMES = [
    'soci',
    'estargz',
    'stargz',
    'esgz',
]

TIME_COLOR_PALETTE = [
    '#546E7A',
    '#90A4AE',
    '#CFD8DC',
]


SCRIPTS = {
    'bin-bash': {
        'dark': '#C62828',
        'medium': '#EF5350',
        'light': '#EF9A9A',
    },
    'python-print': {
        'dark': '#2E7D32',
        'medium': '#66BB6A',
        'light': '#A5D6A7',
    },
    'root-python': {
        'dark': '#0277BD',
        'medium': '#29B6F6',
        'light': '#81D4FA',
    },
    'root-fillrandom': {
        'dark': '#4527A0',
        'medium': '#7E57C2',
        'light': '#B39DDB',
    },
}





LEGEND_COLOR = '#ECEFF1'


def is_date(string):
    return re.search('[0-9]{4}-[0-9]{2}-[0-9]{2}T.*', string)


def format_difference(
        left: str,
        right: str,
):
    assert is_date(left)
    assert is_date(right)
    left = string_to_datetime(left)
    right = string_to_datetime(right)

    time_difference = (left - right).total_seconds()
    return time_difference
    # return f'{left} - {right} = {time_difference} s'


def string_to_datetime(string) -> datetime.datetime:
    return datetime.datetime.strptime(
        string[:-9],
        '%Y-%m-%dT%H:%M:%S,%f',
    )


def parse_results(result_file: pathlib.Path | str) -> list[dict]:
    if not isinstance(result_file, pathlib.Path):
        result_file = pathlib.Path(result_file)
    benchmarks = []
    benchmark = {}
    with open(path) as file:
        for line in file.readlines():
            line = line.strip()

            if '#' in line:
                # Consider '#' to be comments.
                # Have the default behavious to be to ignore them.
                if 'benchmark start' in line.lower():
                    benchmark = {}

                if 'benchmark end' in line.lower():
                    benchmarks.append(benchmark)

                continue

            split_lines = line.split(': ', maxsplit=1)

            if len(split_lines) < 2:
                continue

            key, value = split_lines
            value = value.strip()

            benchmark[key] = value
    return benchmarks


def append_benchmarks(benchmark: dict):
    benchmark = deepcopy(benchmark)
    pull_time = format_difference(
        benchmark['pull_end'],
        benchmark['pull_start'],
    )

    creation_time = format_difference(
        benchmark['container_start'],
        benchmark['run_start'],
    )

    execution_time = format_difference(
        benchmark['container_end'],
        benchmark['container_start'],
    )

    total_time = format_difference(
        benchmark['benchmark_end'],
        benchmark['benchmark_start'],
    )

    benchmark['pull_time'] = pull_time
    benchmark['creation_time'] = creation_time
    benchmark['execution_time'] = execution_time
    benchmark['total_time'] = total_time
    benchmark['missing_time'] = (
        total_time - (pull_time + creation_time + execution_time)
    )

    return benchmark


def remove_snapshotter_name(image: str) -> str:
    for ending in SNAPSHOTTER_IMAGE_NAMES:
        image = image.replace('-' + ending, '')

    return image


def load_yaml(path: pathlib.Path) -> dict:
    with open(path) as file:
        yaml = YAML(typ='safe')
        config = yaml.load(file)
    return config


def format_benchmark(benchmark: dict):
    output = ''

    output += tabulate(
        {
            'keys': benchmark.keys(),
            'values': benchmark.values(),
        },
        headers='keys',
    )

    output += '\n'

    return output


if __name__ == '__main__':
    CONFIG = load_yaml(paths.CONFIG_FILE)
    for key, value in CONFIG['regex-filters'].items():
        if value is None:
            CONFIG['regex-filters'][key] = '.*'

    datetime_regex = '[0-9]{4}-[0-9]{2}-[0-9]{2}T.*'

    results_directory_path = paths.PROJECT_ROOT / CONFIG['results_directory']
    # Remove paths without a datetime string
    unsorted_unfiltered_result_paths = [
        path for path in results_directory_path.iterdir()
        if re.search(datetime_regex, path.name) is not None
    ]

    unfiltered_result_paths = sorted(
        unsorted_unfiltered_result_paths,
        key=lambda x: re.search(datetime_regex, x.name).group(),
        reverse=True,
    )

    result_paths = []
    for path in unfiltered_result_paths:
        name = path.name

        datetime_match = re.search(datetime_regex, name)
        datetime_string = datetime_match.group() if datetime_match is not None else None

        if (
            None not in
            (
                re.search(
                    CONFIG['regex-filters']['filename'],
                    str(path),
                ),
            )
        ):
            result_paths.append(path)

    result_paths = result_paths[:CONFIG['latest']]

    benchmarks = []
    for path in result_paths:
        print(f'Processing: {path.name}')
        benchmarks += parse_results(path)

    benchmarks = [append_benchmarks(benchmark) for benchmark in benchmarks]

    output_df = pd.DataFrame(benchmarks)

    images = output_df['image'].map(remove_snapshotter_name).unique()

    output_dict = {
        'image': [],
        'script': [],
        'runs': [],
        'snapshotter': [],
        'pull_time': [],
        'pull_time_std': [],
        'pull_time_std_%': [],
        'creation_time': [],
        'creation_time_std': [],
        'creation_time_std_%': [],
        'execution_time': [],
        'execution_time_std': [],
        'execution_time_std_%': [],
        'bytes': [],
        'bytes_std': [],
        'bytes_std_%': [],
    }
    for image in images:
        filtered_df_1 = output_df[
            [image in i for i in output_df['image']]
        ]

        fig_time, axs_time = plt.subplots(
            nrows=2,
            ncols=1,
            figsize=(10, 10),
            sharex=True,
        )

        time_min = math.inf
        time_max = - math.inf


        fig_data, axs_data = plt.subplots(
            nrows=2,
            ncols=1,
            figsize=(10, 10),
            sharex=True,
        )


        scripts = filtered_df_1['script'].unique()

        script_names = [
            script.split('/')[-1].split('.')[0]
            for script in scripts
        ]

        scripts_in_image = []
        for script in script_names:
            if script in SCRIPTS:
                scripts_in_image.append(script)

        for script in scripts:
            script_name = script.split('/')[-1].split('.')[0]
            filtered_df_2 = filtered_df_1[filtered_df_1['script'] == script]
            snapshotters = filtered_df_2['snapshotter'].unique()
            snapshotter_labels = [
                snapshotter
                if 'overlayfs' not in snapshotter
                else 'overlayfs\n(default)'
                for snapshotter in snapshotters
            ]

            snapshotter_label_indices = list(range(len(snapshotter_labels)))



            image_name = image.split('/')[-1]

            for snapshotter, snapshotter_label in zip(snapshotters, snapshotter_labels):
                filtered_df_3 = filtered_df_2[
                    filtered_df_2['snapshotter'] == snapshotter
                ]

                run_count = len(filtered_df_3)
                pull_time = filtered_df_3['pull_time'].mean()
                pull_time_std = filtered_df_3['pull_time'].std()
                pull_time_std_proportion = pull_time_std / pull_time

                creation_time = filtered_df_3['creation_time'].mean()
                creation_time_std = filtered_df_3['creation_time'].std()
                creation_time_std_proportion = creation_time_std / creation_time

                execution_time = filtered_df_3['execution_time'].mean()
                execution_time_std = filtered_df_3['execution_time'].std()
                execution_time_std_proportion = execution_time_std / execution_time

                bytes = filtered_df_3['bytes'].astype(int).mean()
                bytes_std = filtered_df_3['bytes'].astype(int).std()
                bytes_std_proportion = bytes_std / bytes

                output_dict['image'].append(image)
                output_dict['script'].append(script)
                output_dict['runs'].append(run_count)
                output_dict['snapshotter'].append(snapshotter)

                output_dict['pull_time'].append(pull_time)
                output_dict['pull_time_std'].append(pull_time_std)
                output_dict['pull_time_std_%'].append(
                    100 * pull_time_std_proportion,
                )

                output_dict['creation_time'].append(creation_time)
                output_dict['creation_time_std'].append(creation_time_std)
                output_dict['creation_time_std_%'].append(
                    100 * creation_time_std_proportion,
                )

                output_dict['execution_time'].append(execution_time)
                output_dict['execution_time_std'].append(execution_time_std)
                output_dict['execution_time_std_%'].append(
                    100 * execution_time_std_proportion,
                )

                output_dict['bytes'].append(bytes)
                output_dict['bytes_std'].append(bytes_std)
                output_dict['bytes_std_%'].append(
                    100 * bytes_std_proportion,
                )

                if script_name in scripts_in_image:
                    bar_index = scripts_in_image.index(script_name)

                    bar_position = (
                        bar_index
                        - (
                            (len(scripts_in_image) - 1)
                            / 2
                        )
                    )

                    snapshotter_index = list(snapshotters).index(snapshotter)

                    if pull_time < time_min:
                        time_min = pull_time
                    if pull_time + creation_time + execution_time > time_max:
                        time_max = pull_time + creation_time + execution_time

                    spacing = (
                        1
                        if len(scripts_in_image) == 1
                        else 1 / (len(scripts_in_image) + 1)
                    )
                    width = 0.9 * spacing

                    megabytes = bytes / 1_000_000
                    for i, ax in enumerate(axs_data):
                        log = False
                        if i == 1:
                            log = True

                        ax.bar(
                            snapshotter_label_indices[snapshotter_index] + spacing * bar_position,
                            megabytes,
                            width=width,
                            color=SCRIPTS[script_name]['medium'],
                            log=log,
                            hatch='x',
                        )

                    for i, ax in enumerate(axs_time):
                        log = False
                        if i == 1:
                            log = True

                        ax.bar(
                            snapshotter_label_indices[snapshotter_index] + spacing * bar_position,
                            pull_time,
                            width=width,
                            color=SCRIPTS[script_name]['dark'],
                            log=log,

                        )

                        ax.bar(
                            snapshotter_label_indices[snapshotter_index] + spacing * bar_position,
                            creation_time,
                            bottom=pull_time,
                            width=width,
                            color=SCRIPTS[script_name]['medium'],
                            log=log,

                        )

                        ax.bar(
                            snapshotter_label_indices[snapshotter_index] + spacing * bar_position,
                            execution_time,
                            bottom=pull_time + creation_time,
                            width=width,
                            color=SCRIPTS[script_name]['light'],
                            log=log,

                        )

                # -- END FOR SNAPSHOTTER --
            # -- END FOR SCRIPT --

        fig_data.legend(
            handles=[
                Patch(
                    facecolor=SCRIPTS[script]['medium'],
                    label=script,
                ) for script in scripts_in_image
            ],
            loc='upper center',
            bbox_to_anchor=(0.5525, 0.94),
            facecolor=LEGEND_COLOR,
            ncol=4,
        )

        for ax in axs_data:
            ax.set_xticks(
                snapshotter_label_indices,
                snapshotter_labels,
            )
            ax.grid([], axis='x')
            ax.minorticks_on()
            ax.grid(
                axis='y',
                which='minor',
                linestyle='-',
                linewidth=0.8,
                alpha=0.5,
            )
            ax.set_ylabel('Data [MB]')

        fig_data.suptitle(f'{image_name}\n')
        # buffer = 0.75
        # axs_time[1].set_ylim(
        #     [
        #         buffer * time_min,
        #         (buffer**-1) * time_max,
        #         ]
        # )
        fig_data.supxlabel('Snapshotter')
        plot_path = paths.PLOT_DIR / f'{image_name}-data.png'

        fig_data.savefig(
            plot_path,
        )
        print(
            f'Saved plot: {plot_path.name}',
        )





        fig_time.legend(
            handles=[
                Patch(
                    facecolor=SCRIPTS[script]['medium'],
                    label=script,
                ) for script in scripts_in_image
            ],
            loc='upper center',
            bbox_to_anchor=(0.545, 0.895),
            facecolor=LEGEND_COLOR,
            ncol=4,
        )

        for ax in axs_time:
            ax.set_xticks(
                snapshotter_label_indices,
                snapshotter_labels,
            )
            ax.grid([], axis='x')
            ax.minorticks_on()
            ax.grid(
                axis='y',
                which='minor',
                linestyle='-',
                linewidth=0.8,
                alpha=0.5,
            )
            ax.set_ylabel('Time [s]')

        fig_time.suptitle(
            f'{image_name}\ndark=pull, medium=create, light=run\n',
        )
        buffer = 0.75
        axs_time[1].set_ylim(
            [
                buffer * time_min,
                (buffer**-1) * time_max,
            ]
        )
        fig_time.supxlabel('Snapshotter')
        plot_path = paths.PLOT_DIR / f'{image_name}-time.png'

        fig_time.savefig(
            plot_path,
        )
        print(
            f'Saved plot: {plot_path.name}',
        )
        # fig_multibar.show()
        # -- END FOR IMAGE --

    output_df = pd.DataFrame(output_dict)
    output_file = paths.OUTPUT_DIR / 'output.csv'
    output_df.to_csv(
        paths.OUTPUT_DIR / 'output.csv',
        index=False,
    )

    OUTPUT_INPUTS = paths.OUTPUT_DIR / 'output_inputs'
    OUTPUT_INPUTS.mkdir(parents=True, exist_ok=True)

    DATA_USED = OUTPUT_INPUTS / 'raw_data_copy'
    DATA_USED.mkdir(parents=True, exist_ok=True)

    for path in result_paths:
        shutil.copy(path, DATA_USED)

    with open(OUTPUT_INPUTS / 'config.yaml', 'w') as file:
        yml = YAML()
        yml.dump(CONFIG, file)

    print(
        f'\nPROGRAM COMPLETE'
        f'\n\nPlots saved to:\n{paths.PLOT_DIR}'
        f'\n\nMore information saved to:\n{output_file}',
    )
