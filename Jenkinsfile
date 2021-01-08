// Example Jenkins build file, you will need to update the repository location and authentication
pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr: '5'))
        retry(2)
        timeout(time: 2, unit: 'HOURS')
        gitLabConnection("${CONNECTION URL HERE}/${env.BRANCH_NAME}")
    }
    triggers {
        cron('H H(1-5) * * *') // Run every morning between 1 and 6
        pollSCM('H/5 * * * *') // Poll every 5 minutes
        gitlab(triggerOnPush: true, triggerOnMergeRequest: true, branchFilterType: 'All') // Gitlab doesn't seem to be working yet.
    }
    environment {
        NO_PROXY='127.0.0.1,localhost'
        no_proxy='127.0.0.1,localhost'
    }
    stages {
        stage('clone') {
            steps {
                sh "printenv"
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "origin/${env.BRANCH_NAME}"]],
                    doGenerateSubmoduleConfigurations: false,
                    extensions: [[$class: 'SubmoduleOption',
                        disableSubmodules: false,
                        parentCredentials: true,
                        recursiveSubmodules: true,
                        reference: '',
                        trackingSubmodules: false]],
                    submoduleCfg: [],
                    userRemoteConfigs: [[credentialsId: 'gitlab_project_demodocus_framework',
                    url: "${REPOSITORY URL HERE}"]]
                ])
            }
        }
        stage('build') {
            steps {
                sh script: ''' #!/bin/bash
                source /opt/rh/rh-python36/enable
                python -m venv ENV
                source ENV/bin/activate
                python -V
                pip install --upgrade pip
                pip install -Ur requirements.txt

                echo "Pulling chromedriver version -- $(curl https://chromedriver.storage.googleapis.com/LATEST_RELEASE_`expr substr "$(google-chrome --version)" 15 9`)"
                wget "https://chromedriver.storage.googleapis.com/$(curl https://chromedriver.storage.googleapis.com/LATEST_RELEASE_`expr substr "$(google-chrome --version)" 15 9`)/chromedriver_linux64.zip"
                unzip -d ENV/bin chromedriver_linux64.zip
                '''
            }
        }
        stage('test_dom_manipulations') {
            steps {
                runShortTest('demodocusfw/tests/dom_manipulations.py')
            }
        }
        stage('test_compare') {
            steps {
                runShortTest('demodocusfw/tests/compare.py')
            }
        }
        stage('test_reachable') {
            steps {
                runShortTest('demodocusfw/tests/reachable.py')
            }
        }
        stage('test_selenium_integration') {
            steps {
                runShortTest('demodocusfw/tests/selenium_integration.py')
            }
        }
        stage('test_web_access_chrome') {
            steps {
                runShortTest('demodocusfw/tests/test_web_access_chrome.py')
            }
        }
        stage('test_event_tracking') {
            steps {
                runShortTest('demodocusfw/tests/event_tracking.py')
            }
        }
        stage('test_animation') {
            steps {
                runShortTest('demodocusfw/tests/animation.py')
            }
        }
        stage('test_crawler') {
            steps {
                runShortTest('demodocusfw/tests/crawler.py')
            }
        }
        stage('test_crawl_graph') {
            steps {
                runShortTest('demodocusfw/tests/crawler.py')
            }
        }
        stage('test_reduced_crawl') {
            steps {
                runShortTest('demodocusfw/tests/reduced_crawl.py')
            }
        }
        stage('test_analysis') {
            steps {
                runShortTest('demodocusfw/tests/analysis.py')
            }
        }
        stage('test_keyboard_eval') {
            steps {
                runShortTest('demodocusfw/tests/keyboard_eval.py')
            }
        }
    }
    post { // Make to always try and clean the workspace
        always {
            echo 'Finished build'
            cleanWs()
        }
        success {
            echo 'Successfully cleaned workspace.'
        }
        failure {
            echo 'Failed to clean workspace.'
        }
    }
}

// we need to ensure the env variables are always correct.
// NOTE: function not used, but built for use in future
//       dev branches.
def runFullTest(testName) {
    // Slight trick, since it uses '$' as a variable,
    // we need to escape that symbol within the string
    sh """#!/bin/bash
    export PATH=\$PATH:ENV/bin
    export PYTHONPATH=src/:\$PYTHONPATH
    export DEM_RUN_EXTENDED=True
    source ENV/bin/activate
    python -m unittest ${testName}
    """
}

def runShortTest(testName) {
    sh """#!/bin/bash
    export PATH=\$PATH:ENV/bin
    export PYTHONPATH=src/:\$PYTHONPATH
    DEM_RUN_EXTENDED=False
    source ENV/bin/activate
    python -m unittest ${testName}
    """
}
