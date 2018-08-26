import logging

import dash
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import pandas as pd
from dash.dependencies import Input
from dash.dependencies import Output
from flask import request
from plotly.graph_objs import Bar
from plotly.graph_objs import Scatter
from plotly.graph_objs import Table

from orderbookmdp.order_book.constants import BUY

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


def get_dist_app():
    layout = html.Div([
        html.Div(className='twelve columns', children=[

            html.Div(className='row', children=[

                html.Div(className='eight columns', children=[

                    html.Div(className='row', children=[
                        dcc.Graph(id='price'),
                        dcc.Interval(id='update', interval=750, n_intervals=0)
                    ]),

                    html.Div(className='row', children=[

                        html.Div(className='six columns', children=[
                            dcc.Graph(id='portfolio'),
                            dcc.Interval(id='update2', interval=250, n_intervals=0)
                        ]),

                        html.Div(className='six columns', children=[
                            dcc.Graph(id='book'),
                            dcc.Interval(id='update3', interval=250, n_intervals=0)
                        ])

                    ])

                ]),

                html.Div(className='four columns', children=[
                    dcc.Graph(id='trades'),
                    dcc.Interval(id='update4', interval=500, n_intervals=0)
                ])
            ])
        ])
    ])
    app = dash.Dash('Trading-App')
    app.layout = layout

    @app.callback(Output('trades', 'figure'), [Input('update4', 'n_intervals')])  # noqa: EF811
    def update(interval):
        trades = pd.DataFrame(app.trades_, columns=['Time', 'Size', 'Price', 'Side'])
        trades['color'] = 'rgb(255,0,0)'
        trades.loc[trades.Side == BUY, 'color'] = 'rgb(0,255,0)'

        trace = Table(
            columnwidth=[50, 20, 30, 15],
            header=dict(values=['Time', 'Size', 'Price', 'Side'],
                        line=dict(color='#7D7F80'),
                        fill=dict(color='#a1c3d1'),
                        align='left'),
            cells=dict(values=[pd.to_datetime(trades.Time), trades.Size.round(4), trades.Price, trades.Side],
                       line=dict(color='#7D7F80'),
                       fill=dict(color=[trades.color]),
                       align='left')
        )

        layout = dict(
            title='Trades',
            height=1100
        )
        return {'data': [trace], 'layout': layout}

    @app.callback(Output('price', 'figure'), [Input('update', 'n_intervals')])  # noqa: EF811
    def update(interval):
        time = list(app.time)
        ask = Scatter(
            y=list(app.ask),
            x=time,
            name='ask'
        )
        bid = Scatter(
            y=list(app.bid),
            x=time,
            name='bid'
        )

        layout = dict(
            title='Price',
        )

        return {'data': [bid, ask], 'layout': layout}

    @app.callback(Output('book', 'figure'), [Input('update3', 'n_intervals')])  # noqa: EF811
    def update(interval):
        buy = Bar(
            x=np.log(1 + np.array(list(app.buybook.values()))),
            y=list(app.buybook.keys()),
            name='Buy Orders',
            orientation='h'
        )

        sell = Bar(
            x=np.log(1 + np.array(list(app.sellbook.values()))),
            y=list(app.sellbook.keys()),
            name='Sell Orders',
            orientation='h'
        )
        layout = dict(
            title='OrderBook',
            xaxis=dict(
                range=[0, np.log(30)]
            )
        )

        return {'data': [buy, sell], 'layout': layout}

    @app.callback(Output('portfolio', 'figure'), [Input('update2', 'n_intervals')])  # noqa: EF811
    def update(interval):

        traces = [Bar(
            x=list(app.buyorders.values()),
            y=list(app.buyorders.keys()),
            name='Buy Orders',
            orientation='h'
        ), Bar(
            x=list(app.sellorders.values()),
            y=list(app.sellorders.keys()),
            name='Sell Orders',
            orientation='h'
        )]

        if app.render_state:
            action, buy_prices, buy_sizes, sell_prices, sell_sizes = app.render_state[0:5]

            traces.append(Scatter(
                x=buy_sizes,
                y=buy_prices,
                name='Buy Dist',
            ))

            traces.append(Scatter(
                x=sell_sizes,
                y=sell_prices,
                name='Sell Dist',
            ))

        layout = dict(
            title='Portfolio',
            xaxis=dict(
                autorange='reversed',
                range=[0, 0.2]
            ),
            yaxis=dict(
                side='right'
            ),
            legend=dict(
                x=10,
                y=10
            )
        )

        return {'data': traces, 'layout': layout}

    @app.server.route('/shutdown', methods=['POST'])
    def shutdown():
        shutdown_server()
        return 'Server shutting down...'

    app.css.append_css({
        'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'
    })

    return app


def get_portfolio_app():
    layout = html.Div([
        html.Div(className='twelve columns', children=[

            html.Div(className='row', children=[

                html.Div(className='eight columns', children=[

                    html.Div(className='row', children=[
                        dcc.Graph(id='price'),
                        dcc.Interval(id='update', interval=750, n_intervals=0)
                    ]),

                    html.Div(className='row', children=[

                        html.Div(className='six columns', children=[

                            dcc.Graph(id='book'),
                            dcc.Interval(id='update3', interval=250, n_intervals=0)
                        ]),

                        html.Div(className='six columns', children=[
                            dcc.Graph(id='portfolio'),
                            dcc.Interval(id='update5', interval=250, n_intervals=0)
                        ])

                    ])

                ]),

                html.Div(className='four columns', children=[
                    dcc.Graph(id='trades'),
                    dcc.Interval(id='update4', interval=100, n_intervals=0)
                ])
            ])
        ])
    ])
    app = dash.Dash('Trading-App')
    app.layout = layout

    @app.callback(Output('trades', 'figure'), [Input('update4', 'n_intervals')])  # noqa: EF811
    def update(interval):
        trades = pd.DataFrame(app.trades_, columns=['Time', 'Size', 'Price', 'Side'])
        trades['color'] = 'rgb(255,0,0)'
        trades.loc[trades.Side == BUY, 'color'] = 'rgb(0,255,0)'

        trace = Table(
            columnwidth=[50, 20, 30, 15],
            header=dict(values=['Time', 'Size', 'Price', 'Side'],
                        line=dict(color='#7D7F80'),
                        fill=dict(color='#a1c3d1'),
                        align='left'),
            cells=dict(values=[pd.to_datetime(trades.Time), trades.Size.round(4), trades.Price, trades.Side],
                       line=dict(color='#7D7F80'),
                       fill=dict(color=[trades.color]),
                       align='left')
        )

        layout = dict(
            title='Trades',
            height=1100
        )
        return {'data': [trace], 'layout': layout}

    @app.callback(Output('price', 'figure'), [Input('update', 'n_intervals')])  # noqa: EF811
    def update(interval):
        time = list(app.time)
        ask = Scatter(
            y=list(app.ask),
            x=time,
            name='ask'
        )
        bid = Scatter(
            y=list(app.bid),
            x=time,
            name='bid'
        )

        possession = Scatter(
            y=list(app.possession),
            x=time,
            name='possession',
            yaxis='y2',
            opacity=0.3
        )

        layout = dict(
            title='Price',
            yaxis=dict(title='Price'),
            yaxis2=dict(title='Possession', overlaying='y', side='right', ymin=0)
        )

        return {'data': [bid, ask, possession], 'layout': layout}

    @app.callback(Output('portfolio', 'figure'), [Input('update', 'n_intervals')])  # noqa: EF811
    def update(interval):
        time = list(app.time)
        capital_change = Scatter(
            y=list(app.capital_change),
            x=time,
            name='capital_change',
        )

        layout = dict(
            title='Portfolio',
            yaxis=dict(title='% of original capital', ymin=0)
        )

        return {'data': [capital_change], 'layout': layout}

    @app.callback(Output('book', 'figure'), [Input('update3', 'n_intervals')])  # noqa: EF811
    def update(interval):
        buy = Bar(
            x=np.log(1 + np.array(list(app.buybook.values()))),
            y=list(app.buybook.keys()),
            name='Buy Orders',
            orientation='h'
        )

        sell = Bar(
            x=np.log(1 + np.array(list(app.sellbook.values()))),
            y=list(app.sellbook.keys()),
            name='Sell Orders',
            orientation='h'
        )
        layout = dict(
            title='OrderBook',
            xaxis=dict(
                range=[0, np.log(30)]
            )
        )

        return {'data': [buy, sell], 'layout': layout}

    @app.server.route('/shutdown', methods=['POST'])
    def shutdown():
        shutdown_server()
        return 'Server shutting down...'

    app.css.append_css({
        'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'
    })

    return app


def get_multienv_app():
    layout = html.Div([
        html.Div(className='twelve columns', children=[

            html.Div(className='row', children=[

                html.Div(className='eight columns', children=[

                    html.Div(className='row', children=[
                        dcc.Graph(id='price'),
                        dcc.Interval(id='update', interval=750, n_intervals=0)
                    ]),

                    html.Div(className='row', children=[

                        dcc.Graph(id='book'),
                        dcc.Interval(id='update3', interval=250, n_intervals=0)

                    ])

                ]),

                html.Div(className='four columns', children=[
                    dcc.Graph(id='trades'),
                    dcc.Interval(id='update4', interval=100, n_intervals=0)
                ])
            ])
        ])
    ])
    app = dash.Dash('Trading-App')
    app.layout = layout

    @app.callback(Output('trades', 'figure'), [Input('update4', 'n_intervals')])  # noqa: EF811
    def update(interval):
        trades = pd.DataFrame(app.trades_, columns=['T_ID', 'TC_ID', 'Price', 'Size', 'O_ID', 'Side', 'Time'])
        trades['color'] = 'rgb(255,0,0)'
        trades.loc[trades.Side == BUY, 'color'] = 'rgb(0,255,0)'

        trace = Table(
            columnwidth=[80, 20, 30, 15, 10],
            header=dict(values=['Time', 'Size', 'Price', 'Side', 'Trader'],
                        line=dict(color='#7D7F80'),
                        fill=dict(color='#a1c3d1'),
                        align='left'),
            cells=dict(
                values=[pd.to_datetime(trades.Time), trades.Size.round(4), trades.Price, trades.Side, trades.T_ID],
                line=dict(color='#7D7F80'),
                fill=dict(color=[trades.color]),
                align='left')
        )

        layout = dict(
            title='Trades',
            height=1100
        )
        return {'data': [trace], 'layout': layout}

    @app.callback(Output('price', 'figure'), [Input('update', 'n_intervals')])  # noqa: EF811
    def update(interval):
        time = list(app.time)
        ask = Scatter(
            y=list(app.ask),
            x=time,
            name='ask'
        )
        bid = Scatter(
            y=list(app.bid),
            x=time,
            name='bid'
        )

        layout = dict(
            title='Price',
            yaxis=dict(title='Price'),
        )

        return {'data': [bid, ask], 'layout': layout}

    @app.callback(Output('book', 'figure'), [Input('update3', 'n_intervals')])  # noqa: EF811
    def update(interval):
        buy = Bar(
            y=list(app.buybook.values()),
            x=list(app.buybook.keys()),
            name='Buy Orders',
        )

        sell = Bar(
            y=list(app.sellbook.values()),
            x=list(app.sellbook.keys()),
            name='Sell Orders',
        )
        layout = dict(
            title='OrderBook',
        )

        return {'data': [buy, sell], 'layout': layout}

    @app.server.route('/shutdown', methods=['POST'])
    def shutdown():
        shutdown_server()
        return 'Server shutting down...'

    app.css.append_css({
        'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'
    })

    return app
