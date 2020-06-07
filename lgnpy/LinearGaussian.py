import pandas as pd
import numpy as np
import networkx as nx
import numbers
import math
import copy
from .Graph import Graph
import warnings
from .logging_config import Logger

log = Logger()


class LinearGaussian(Graph):
    def __init__(self):
        super().__init__()

    def __get_node_values(self, node):
        """
    Get mean and variance of node using Linear Gaussian CPD. Calcluated using finding betas
    """
        index_to_keep = [self.nodes.index(node)]
        index_to_reduce = [self.nodes.index(idx) for idx in list(self.g.pred[node])]
        values = self.__get_parent_calculated_means(list(self.g.pred[node]))

        mu_j = self.mean[index_to_keep]
        mu_i = self.mean[index_to_reduce]

        sig_i_j = self.cov[np.ix_(index_to_reduce, index_to_keep)]
        sig_j_i = self.cov[np.ix_(index_to_keep, index_to_reduce)]
        sig_i_i_inv = np.linalg.inv(self.cov[np.ix_(index_to_reduce, index_to_reduce)])
        sig_j_j = self.cov[np.ix_(index_to_keep, index_to_keep)]

        covariance = sig_j_j - np.dot(np.dot(sig_j_i, sig_i_i_inv), sig_i_j)
        beta_0 = mu_j - np.dot(np.dot(sig_j_i, sig_i_i_inv), mu_i)
        beta = np.dot(sig_j_i, sig_i_i_inv)

        new_mu = beta_0 + np.dot(beta, values)
        self.parameters[node] = {"beta": list(beta_0) + list(beta[0])}

        return new_mu[0], covariance[0][0]

    def __get_parent_calculated_means(self, nodes):
        """
    Get evidences of parents given node name list
    """
        pa_e = []
        for node in nodes:
            ev = self.calculated_means[node]
            if ev is None:
                ev = self.mean[self.nodes.index(node)]
            pa_e.append(ev)
        return pa_e

    def get_model_parameters(self):
        """
    Get parameters for each node
    """
        return self.parameters

    def __build_results(self):
        """
        Make Pandas dataframe with the results.

        """

        self.inf_summary = pd.DataFrame(
            index=self.nodes,
            columns=[
                "Evidence",
                "Mean",
                "Mean_inferred",
                "Variance",
                "Variance_inferred",
            ],
        )

        self.inf_summary.loc[:, "Mean"] = self.mean
        self.inf_summary["Evidence"] = self.inf_summary.index.to_series().map(
            self.evidences
        )
        self.inf_summary.loc[:, "Variance"] = np.diag(self.cov)


        self.inf_summary["Mean_inferred"] = self.inf_summary.index.to_series().map(
            self.calculated_means
        )
        self.inf_summary["Variance_inferred"] = self.inf_summary.index.to_series().map(
            self.calculated_vars
        )
        self.inf_summary["u_%change"] = (
            (self.inf_summary["Mean_inferred"] - self.inf_summary["Mean"]) / self.inf_summary["Mean"]
        ) * 100

        self.inf_summary = (
            self.inf_summary.round(4)
            .replace(pd.np.nan, "", regex=True)
            .replace(0, "", regex=True)
        )
        return self.inf_summary

    def run_inference(self, debug=True, return_results=True):
        """
        Run Inference on network with given evidences.
        """

        _log = log.setup_logger(debug=debug)
        _log.debug("Started")

        self.parameters = dict.fromkeys(self.nodes)
        if all(x == None for x in self.evidences.values()):
            _log.debug("No evidence was set. Proceeding without evidence")
        root_nodes = [
            x
            for x in self.g.nodes()
            if self.g.out_degree(x) >= 1 and self.g.in_degree(x) == 0
        ]
        print("initial root nods")
        print(root_nodes)
        self.calculated_means = copy.deepcopy(self.evidences)
        self.calculated_vars = dict.fromkeys(self.nodes)
        self.done_flags = dict.fromkeys(self.nodes)

        for node in root_nodes:
            self.done_flags[node] = True

        while not all(x == True for x in self.done_flags.values()):
            next_root_nodes = copy.deepcopy(root_nodes)
            root_nodes = []
            for node in next_root_nodes:
                _log.debug( f"Calculating children of {node} : {list(self.g.succ[node].keys())}")
                if self.calculated_means[node] == None:
                    self.calculated_means[node] = self.mean[self.nodes.index(node)]
                    _log.debug(f"Evidence was not available for node {node}, so took mean.")
                for child in self.g.succ[node]:
                    if self.done_flags[child] != True:
                        (
                            self.calculated_means[child],
                            self.calculated_vars[child],
                        ) = self.__get_node_values(child)
                        _log.debug(f"\tcalculated for {child}")
                        self.done_flags[child] = True
                        root_nodes.append(child)
                    else:
                        _log.debug(f"\t{child} already calculated")

        return self.__build_results()

    def run_inference2(self, debug=True, return_results=True):
        """
        Run Inference 2 on network with given evidences.
        """

        _log = log.setup_logger(debug=debug)
        _log.debug("Started")

        self.parameters = dict.fromkeys(self.nodes)
        if all(x == None for x in self.evidences.values()):
            _log.debug("No evidence was set. Proceeding without evidence")
        root_nodes = [
            x
            for x in self.g.nodes()
            if self.g.out_degree(x) >= 1 and self.g.in_degree(x) == 0
        ]
        # for node in root_nodes:
        #     children =  self.get_children(node)
        #     for paren


        print("initial root nods")
        print(root_nodes)
        self.calculated_means = copy.deepcopy(self.evidences)
        self.calculated_vars = dict.fromkeys(self.nodes)
        self.done_flags = dict.fromkeys(self.nodes)

        for node in root_nodes:
            self.done_flags[node] = True

        while not all(x == True for x in self.done_flags.values()):
            next_root_nodes = copy.deepcopy(root_nodes)
            root_nodes = []
            for node in next_root_nodes:
                _log.debug( f"Calculating children of {node} : {list(self.g.succ[node].keys())}")
                if self.calculated_means[node] == None:
                    self.calculated_means[node] = self.mean[self.nodes.index(node)]
                    _log.debug(f"Evidence was not available for node {node}, so took mean.")
                for child in self.g.succ[node]:
                    if self.done_flags[child] != True:
                        (
                            self.calculated_means[child],
                            self.calculated_vars[child],
                        ) = self.__get_node_values(child)
                        _log.debug(f"\tcalculated for {child}")
                        self.done_flags[child] = True
                        root_nodes.append(child)
                    else:
                        _log.debug(f"\t{child} already calculated")

        return self.__build_results()


    def get_inference_results(self):
        return self.inf_summary
