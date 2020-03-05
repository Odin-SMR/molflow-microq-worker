node {
    checkout scm
    stage('Test') {
        sh "tox -- --runslow --runsystem"
    }
    stage('Build') {
        sh "scripts/build"
        sh "docker build -t docker2.molflow.com/devops/uworker ."
    }
    stage("Push") {
        if (env.GIT_BRANCH == 'origin/master') {
            sh "docker push docker2.molflow.com/devops/uworker"
        }
    }
}