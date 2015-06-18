#!/usr/bin/env python


from flask import Flask, session, redirect, url_for, escape, request
import logging





def hello_world(request, svc_registry, logger):
    logger.info('>>> invoking hello_world handler function...')       
    db_service = svc_registry.lookup('mysql_connector')
    logger.info(db_service.stub_function())
    return 'Hello, World!'


def load_s3_excelfile(request, svc_registry, logger):
    logger.info('>>> invoking load_s3_excelfile handler function...')
    return 'Here is where we will load an excel file from S3.'
