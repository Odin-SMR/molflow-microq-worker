node {
    def uworkerImage
    stage('Git') {
        checkout scm
    }
    stage('Test') {
        sh "tox -- --runslow --runsystem"
    }
    stage('Build') {
        sh "docker build -t docker2.molflow.com/devops/uworker ."
        uworkerImage = docker.build("odinsmr/uworker")
    }
    stage('Cleanup') {
        sh "rm -r .tox"
    }
    if (env.BRANCH_NAME == 'master') {
        stage('push') {
          withDockerRegistry([ credentialsId: "dockerhub-molflowbot", url: "" ]) {
             uworkerImage.push(env.BUILD_TAG)
             uworkerImage.push('latest')
          }
        }
    }
}
