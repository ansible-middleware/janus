# README - Janus

This project, called Janus, is a set of Ansible roles designed to transform a collection from upstream to downstream. This process is somewhat specific to Red Hat. In order to provide certify content over Ansible Automation Hub, collections are required to use the redhat namespace and, in the case of collections related to middleware products (like JBoss EAP or Red Hat SSO), it is also required to change name of the collection from the upstream version (Wildfly, Keycloak) to the downstream one (JBoss EAP, RH SSO).

Janus takes care of the changes required, ensuring that the downstream collections is identical to the upstream, apart for the required naming changes.
