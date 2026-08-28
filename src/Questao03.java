class ImpressoraDeNome implements Runnable {

    private final String nome;

    ImpressoraDeNome(String nome) {
        this.nome = nome;
    }

    @Override
    public void run() {
        for (int i = 0; i < 5; i++) {
            System.out.println(nome);
        }
    }
}

public class Questao03 {

    public static void main(String[] args) {

        Thread threadA = new Thread(new ImpressoraDeNome("Thread A"));
        Thread threadB = new Thread(new ImpressoraDeNome("Thread B"));
        Thread threadC = new Thread(new ImpressoraDeNome("Thread C"));

        threadA.start();
        threadB.start();
        threadC.start();
    }
}
